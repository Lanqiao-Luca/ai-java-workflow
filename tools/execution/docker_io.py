"""Bounded local Docker CLI and source-only tar exchange. Never extract arbitrary tar."""
from pathlib import Path,PurePosixPath
import hashlib
import io
import json
import os
import selectors
import stat
import subprocess
import tarfile
import time
from .runtime import Rejected,relative

MAX_ARCHIVE=8*1024*1024
MAX_FILE=1024*1024
MAX_FILES=256


def source_files(root):
    root=Path(root);files={}
    for path in sorted(root.rglob('*')):
        if path==root/'.git':continue
        relative(path.relative_to(root).as_posix())
        if path.is_symlink() or not (path.is_dir() or stat.S_ISREG(path.stat().st_mode)):
            raise Rejected('unsupported source object')
        if path.is_file():
            if path.stat().st_size>MAX_FILE:raise Rejected('source file limit')
            files[path.relative_to(root).as_posix()]={'data':path.read_bytes(),'mode':stat.S_IMODE(path.stat().st_mode)&0o777}
    if len(files)>MAX_FILES:raise Rejected('source count limit')
    return files


def manifest(files):
    return {n:{'sha256':hashlib.sha256(v['data']).hexdigest(),'mode':v['mode']} for n,v in sorted(files.items())}


def pack(files):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w') as archive:
        for name,value in sorted(files.items()):
            relative(name)
            info=tarfile.TarInfo(name);info.uid=1000;info.gid=1000;info.mode=value['mode'];info.size=len(value['data']);info.mtime=946684800
            archive.addfile(info,io.BytesIO(value['data']))
    data=buffer.getvalue()
    if len(data)>MAX_ARCHIVE:raise Rejected('source archive limit')
    return data


def unpack(data, prefix=''):
    if len(data)>MAX_ARCHIVE:raise Rejected('output archive limit')
    files={};count=0
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as archive:
        for member in archive:
            count+=1
            if count>MAX_FILES*4:raise Rejected('archive entry limit')
            path=PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts:raise Rejected('archive traversal')
            name=path.as_posix()
            if name=='.' and member.isdir():continue
            if prefix:
                parts=path.parts
                if not parts or parts[0]!=prefix:raise Rejected('unexpected archive prefix')
                name=PurePosixPath(*parts[1:]).as_posix()
                if name=='.' and member.isdir():continue
            relative(name)
            if member.isdir():continue
            if not member.isfile() or member.issparse() or member.size>MAX_FILE or member.mode&0o7000:
                raise Rejected('unsafe archive object')
            if name in files or len(files)>=MAX_FILES:raise Rejected('duplicate or excessive output')
            value=archive.extractfile(member).read(MAX_FILE+1)
            if len(value)!=member.size:raise Rejected('incomplete output')
            files[name]={'data':value,'mode':member.mode&0o777}
    return files


class DockerUnavailable(Rejected):
    pass


class DockerCLI:
    """Only an explicit local Unix socket and dedicated empty CLI configuration."""
    def __init__(self,binary,socket,config):
        self.binary=Path(binary).resolve(strict=True)
        if not self.binary.is_file() or not os.access(self.binary,os.X_OK):raise Rejected('Docker binary required')
        if not isinstance(socket,str) or not socket.startswith('unix:///') or any(c in socket for c in ['\n','\r','\0']):
            raise Rejected('explicit local Unix socket required')
        path=Path(socket[7:]).resolve(strict=True)
        if not stat.S_ISSOCK(path.stat().st_mode):raise Rejected('local Docker socket required')
        self.socket='unix://'+str(path)
        self.config=Path(config).resolve();self.config.mkdir(parents=True,exist_ok=False,mode=0o700)
        (self.config/'home').mkdir()
        self.env={'PATH':'/usr/bin:/bin','HOME':str(self.config/'home'),'LC_ALL':'C','DOCKER_CONFIG':str(self.config)}

    def call(self,args,data=None,timeout=30,limit=MAX_ARCHIVE,check=True):
        if not isinstance(args,list) or not all(isinstance(a,str) and '\0' not in a for a in args):raise Rejected('Docker argv required')
        argv=[str(self.binary),'--config',str(self.config),'--host',self.socket,*args]
        process=subprocess.Popen(argv,stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=self.env)
        selector=selectors.DefaultSelector();buffers={'out':bytearray(),'err':bytearray()};offset=0
        for stream,name in [(process.stdout,'out'),(process.stderr,'err')]:
            os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name)
        if data is not None:
            os.set_blocking(process.stdin.fileno(),False);selector.register(process.stdin,selectors.EVENT_WRITE,'in')
        deadline=time.monotonic()+timeout
        try:
            while selector.get_map():
                if time.monotonic()>=deadline:raise DockerUnavailable('Docker operation timeout; ownership state must be inspected')
                for key,mask in selector.select(min(.1,max(0,deadline-time.monotonic()))):
                    if key.data=='in':
                        if offset==len(data):selector.unregister(key.fileobj);key.fileobj.close();continue
                        try:offset+=os.write(key.fd,data[offset:offset+65536])
                        except BrokenPipeError:selector.unregister(key.fileobj);key.fileobj.close()
                    else:
                        chunk=os.read(key.fd,65536)
                        if not chunk:selector.unregister(key.fileobj);key.fileobj.close();continue
                        buffers[key.data].extend(chunk)
                        if len(buffers[key.data])>(limit if key.data=='out' else 65536):raise DockerUnavailable('Docker output limit')
            process.wait(timeout=max(.1,deadline-time.monotonic()))
            if check and process.returncode:
                (self.config/'last-error.log').write_bytes(bytes(buffers['err']))
                raise DockerUnavailable('Docker operation failed: '+args[0])
            return process.returncode,bytes(buffers['out']),bytes(buffers['err'])
        finally:
            selector.close()
            if process.poll() is None:process.kill();process.wait(timeout=5)
            for stream in [process.stdin,process.stdout,process.stderr]:
                if stream and not stream.closed:stream.close()

    def json(self,args):
        return json.loads(self.call(args,limit=1024*1024)[1])
