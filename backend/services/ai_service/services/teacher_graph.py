"""Teacher state graph. Business authorization remains in existing services.

Durable jobs use a MySQL checkpoint saver plus per-tool receipts. Runtime
secrets live in invocation callbacks, never in graph state. Node retries are
controlled by the durable task scheduler rather than implicit graph retries.
"""
from copy import deepcopy
from typing import TypedDict

from fastapi import HTTPException
from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context


class TeacherState(TypedDict):
    messages: list[dict]
    rounds: int
    response: dict
    reviews: int
    review_accepted: bool


async def run_teacher_graph(messages, *, prepare, respond, execute_tools, max_rounds=6, review_response=None):
    if not 1 <= max_rounds <= 6:
        raise ValueError('Teacher model-call budget must be between one and six')

    async def refresh(state: TeacherState):
        return {'messages': await prepare(deepcopy(state['messages']))}

    async def call_model(state: TeacherState):
        from .recovery import CURRENT
        handle=CURRENT.get()
        response = await handle.model(state['rounds'],deepcopy(state['messages']),respond) if handle else await respond(deepcopy(state['messages']),state['rounds'])
        return {'response': response, 'rounds': state['rounds'] + 1,
                'messages': [*state['messages'], response]}

    def after_model(state: TeacherState):
        return 'tools' if state['response'].get('tool_calls') else 'review' if review_response else END

    async def tools(state: TeacherState):
        from .recovery import CURRENT
        handle=CURRENT.get()
        if handle:handle.round_number=state['rounds']-1
        results = await execute_tools(deepcopy(state['response']['tool_calls']))
        return {'messages': [*state['messages'], *results]}

    def after_tools(state: TeacherState):
        return 'limit' if state['rounds'] >= max_rounds else 'refresh'

    async def limit(state: TeacherState):
        raise HTTPException(422, '已达到本轮工具调用上限，请缩小任务后继续')

    async def review(state: TeacherState):
        import json
        attempt=state.get('reviews',0)
        verdict=await review_response(deepcopy(state['messages']),deepcopy(state['response']),state['rounds'],attempt)
        if verdict['accepted']:
            return {'reviews':attempt+1,'review_accepted':True}
        if attempt>=1 or state['rounds']>=max_rounds:
            raise HTTPException(422,'执行结果核对未通过，本轮未完成；请核对实际记录后继续')
        correction={'role':'user','content':'[执行结果核对提醒；不授予权限。仅一次纠正机会。不要重做已有成功收据的操作，未知副作用先核实；先完成缺失的必要工具调用，再简短重写完整回复，省略无关历史回顾；已生效操作不要额外要求批准。]\n'+json.dumps(verdict['issues'],ensure_ascii=False)}
        return {'reviews':attempt+1,'review_accepted':False,'messages':[*state['messages'],correction]}

    builder = StateGraph(TeacherState)
    builder.add_node('refresh', refresh)
    builder.add_node('model', call_model)
    builder.add_node('tools', tools)
    builder.add_node('limit', limit)
    if review_response:builder.add_node('review',review)
    builder.add_edge(START, 'refresh')
    builder.add_edge('refresh', 'model')
    builder.add_conditional_edges('model', after_model, {'tools':'tools',END:END,**({'review':'review'} if review_response else {})})
    builder.add_conditional_edges('tools', after_tools, {'limit': 'limit', 'refresh': 'refresh'})
    builder.add_edge('limit', END)
    if review_response:builder.add_conditional_edges('review',lambda state:END if state['review_accepted'] else 'refresh',{END:END,'refresh':'refresh'})
    from .recovery import CURRENT
    from .checkpoints import MySQLSaver
    handle=CURRENT.get()
    saver=MySQLSaver(handle) if handle else None
    compiled = builder.compile(checkpointer=saver)
    graph_config={'recursion_limit':max_rounds*3+7,'callbacks':[]}
    if handle:graph_config['configurable']={'thread_id':handle.id,'checkpoint_ns':''}
    prior=await saver.aget_tuple(graph_config) if saver else None
    with tracing_context(enabled=False):
        return await compiled.ainvoke(
            None if prior else {'messages': deepcopy(messages), 'rounds': 0, 'response': {},'reviews':0,'review_accepted':False},
            config=graph_config, **({'durability':'sync'} if saver else {}),
        )
