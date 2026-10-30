"""Fixed parser subprocess, not a sandbox. Input bytes only, no DB or user paths."""
import io,json,sys,zipfile
MAX_INPUT=10*1024*1024
MAX_OUTPUT=200000

def validate_office(data,extension):
    from defusedxml import ElementTree
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist()
        if len(infos)>2000 or sum(i.file_size for i in infos)>50*1024*1024: raise ValueError('Office expansion limit')
        if any(i.flag_bits&1 or i.file_size>20*1024*1024 for i in infos): raise ValueError('Office member limit')
        names={i.filename for i in infos}
        required='word/document.xml' if extension=='.docx' else 'ppt/presentation.xml'
        if required not in names or '[Content_Types].xml' not in names: raise ValueError('Wrong Office format')
        if any('vbaproject' in n.lower() or '/embeddings/' in n.lower() for n in names): raise ValueError('Embedded code is unsupported')
        for info in infos:
            if info.filename.endswith('.rels'):
                for rel in ElementTree.fromstring(z.read(info)).iter():
                    if rel.attrib.get('TargetMode')=='External' and not rel.attrib.get('Type','').endswith('/hyperlink'):
                        raise ValueError('External document resources unsupported')


def classify(data,extension):
    """Container format and content are independent axes; no model/OCR calls.

    Detection is structural, not visual understanding. PDF vector illustrations
    and unusual encodings may need later layout analysis; never claim certainty.
    """
    import re
    images=False;structured=False;hints=[]
    if extension in ('.txt','.md'):
        text=data.decode('utf-8-sig')
        images=bool(re.search(r'!\[[^\]]*\]\s*(?:\(|\[)|<img\b',text,re.I))
        structured=bool(re.search(r'^\s*\|.*\||<table\b|^\s*```|^\s*~~~',text,re.M|re.I))
        if images:hints.append('检测到图片引用，未访问或下载外部图片')
    elif extension in ('.docx','.pptx'):
        validate_office(data,extension)
        from defusedxml import ElementTree
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            images=any('/media/' in n and not n.endswith('/') for n in z.namelist())
            for info in z.infolist():
                if not info.filename.endswith('.xml'):continue
                for element in ElementTree.fromstring(z.read(info)).iter():
                    tag=element.tag.rsplit('}',1)[-1]
                    if tag in ('blip','imagedata','pic','chart'):images=True
                    if tag in ('tbl','oMath','oMathPara'):structured=True
        if images:hints.append('检测到内嵌媒体、图片引用或图表对象')
    elif extension=='.pdf':
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTImage,LTLine,LTRect,LTCurve,LTTextContainer
        text_found=False;graphics=False
        def walk(item):
            nonlocal images,structured,text_found,graphics
            if isinstance(item,LTImage):images=True
            if isinstance(item,LTTextContainer) and item.get_text().strip():text_found=True
            if isinstance(item,(LTLine,LTRect)):structured=True
            elif isinstance(item,LTCurve):graphics=True
            if hasattr(item,'__iter__'):
                for child in item:walk(child)
        for page in extract_pages(io.BytesIO(data)):walk(page)
        # Curves may carry diagrams not extractable as text. Defer conservatively.
        if graphics:images=True;hints.append('检测到矢量图形，按视觉内容保守暂缓')
        if not text_found:hints.append('没有检测到可提取文字，可能需要OCR')
        if not text_found:images=True
        if structured:hints.append('检测到线条或矩形，可能含表格；尚未恢复表格结构')
    else:raise ValueError('Unsupported format')
    category='visual_deferred' if images else 'structured_text' if structured else 'plain_text'
    return {'format':extension.lstrip('.'),'category':category,'has_visual_content':images,
            'has_structure_hints':structured,'method':'structural_rules_v1','notes':hints,
            'limitation':'结构规则检测，不保证识别所有表格、公式或图形；不执行OCR。'}

def parse(data,extension):
    if len(data)>MAX_INPUT: raise ValueError('Input too large')
    if extension=='.pdf' and not data.startswith(b'%PDF-'): raise ValueError('Wrong PDF signature')
    if extension in ('.txt','.md') and b'\x00' in data: raise ValueError('Binary text input')
    classification=classify(data,extension)
    if classification['category']=='visual_deferred':
        return {'text':'','extracted_truncated':False,'classification':classification,'rag_supported':False,
                'reason':'检测到图片、图表、矢量图形或无文字层页面，当前暂不处理此文档，也不建立部分文字索引。'}
    if extension in ('.txt','.md'):
        value=data.decode('utf-8-sig')
        if '\x00' in value: raise ValueError('Binary text input')
    else:
        if extension=='.pdf':
            if not data.startswith(b'%PDF-'): raise ValueError('Wrong PDF signature')
        elif extension in ('.docx','.pptx'): validate_office(data,extension)
        else: raise ValueError('Unsupported format')
        from markitdown import StreamInfo
        from markitdown.converters import PdfConverter,DocxConverter,PptxConverter
        converter={'.pdf':PdfConverter,'.docx':DocxConverter,'.pptx':PptxConverter}[extension]()
        result=converter.convert(io.BytesIO(data),StreamInfo(extension=extension))
        value=result.markdown
    value=value.replace('\x00','').strip()
    if not value: raise ValueError('No extractable text')
    return {'text':value[:MAX_OUTPUT],'extracted_truncated':len(value)>MAX_OUTPUT,
            'classification':classification,'rag_supported':True,'reason':''}

def main():
    # Defense in depth for fixed local parsers; not an OS security boundary.
    def deny(event,args):
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'): raise PermissionError('External execution disabled')
    sys.addaudithook(deny)
    try:
        data=sys.stdin.buffer.read(MAX_INPUT+1)
        output=parse(data,sys.argv[1])
    except Exception: output={'error':'无法提取文字：文件格式、外部资源、大小或内容不受支持；扫描件需OCR，当前未启用。'}
    sys.stdout.buffer.write(json.dumps(output,ensure_ascii=False).encode('utf-8'))
if __name__=='__main__': main()
