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

def parse(data,extension):
    if len(data)>MAX_INPUT: raise ValueError('Input too large')
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
    return {'text':value[:MAX_OUTPUT],'extracted_truncated':len(value)>MAX_OUTPUT}

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
