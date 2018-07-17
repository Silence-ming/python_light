import socket
import threading
import re
import os.path
from urllib.parse import urlparse

from tm import render_template

class server():
    def __init__(self):
        self.host = ""
        self.port = 8888
        self.listen = 512
        self.recvNum=1024
        self.staticDir="static"
        self.ico="1.ico"
        self.staticType=".jpg,.png,.gif,.css,.js,.html"
        self.mimeType={".jpg":"image/jpeg",".png":"image/png",".gif":"image/gif",".css":"text/css",".js":"application/x-javascript",".html":"text/html"}
        self.routeInfo=[]
        self.template_dir="template"
    def route(self,url,methods=["GET"]):
        '''采集路由的信息'''
        def fn(callback):
            obj={}
            obj["params"]=re.findall(r':([^/]+)',url)
            obj["url"]=re.sub(r':[^/]+',"(\w+)",url)
            obj["callback"]=callback
            obj["methods"]=methods
            self.routeInfo.append(obj)
        return fn
    def parse_headers(self,response):
        info=""
        info+=response["headers"]["pool"]+" "+response["headers"]["status_code"]+"\r\n"
        info+="content-type:"+response["headers"]["content-type"]+"\r\n\r\n"

        return info.encode(encoding="utf8")

    def route_handle(self,requestData,clientTcp):
        '''请求的动态的路由做处理'''
        flag=True
        for item in self.routeInfo:
            reg=item["url"]
            result=re.match(r'%s'%(reg),requestData["path"])
            if  result and item["methods"].count(requestData["type"])>0:
                for item1 in range(len(item["params"])):
                    requestData["params"][item["params"][item1]]=result.group(item1+1)

                flag=False
                response={}
                response["headers"]={}
                response["headers"]["pool"]="HTTP/1.1"
                response["headers"]["status_code"]="200 ok"
                response["headers"]["content-type"]="text/html;charset=utf-8"
                body=item["callback"](requestData,response)
                headers=self.parse_headers(response)
                clientTcp.send(headers+body.encode(encoding="utf8"))
                clientTcp.close()
                break
        if flag:

            clientTcp.send("this page not find")
            clientTcp.close()

    def requestData_handle(self,requestData):
        '''对请求的数据进行格式化'''
        obj={}
        requestInfo = (requestData.decode(encoding="utf8").splitlines())
        if len(requestInfo)>0:
            firstInfo = requestInfo[0]
            type=re.match(r'[^\s]+',firstInfo).group(0)
            obj["type"]=type
            requestUrl = urlparse(re.match(r'\w+\s+(/[^\s]*)', firstInfo).group(1))

            obj["path"]=requestUrl[2]
            obj["query"]={}
            obj["params"]={}
            if requestUrl[4]:
                for item in requestUrl[4].split("&"):
                    arr=item.split("=")
                    obj["query"][arr[0]]=arr[1]


        return obj

    def request_handle(self,requestData,clientTcp):
        '''处理请求的逻辑'''
        requestUrl=requestData["path"]
        if requestUrl=="/favicon.ico":
            try:
                fobj=open(self.ico,"rb")
                content=fobj.read()
                fobj.close()
                clientTcp.send(b"HTTP/1.1 200 OK\r\ncontent-type:image/x-icon\r\n\r\n"+content)
                clientTcp.close()
            except:
                clientTcp.send(b"HTTP/1.1 404 not find")
                clientTcp.close()
        elif self.staticType.find(os.path.splitext(requestUrl)[1])>-1 and os.path.splitext(requestUrl)[1]:
            if os.path.isdir(self.staticDir):

                fullpath=os.path.join(self.staticDir,requestUrl[1:])

                if os.path.isfile(fullpath):
                    fobj=open(fullpath,"rb")
                    con=fobj.read()
                    fobj.close()
                    clientTcp.send(("HTTP/1.1 200 OK\r\ncontent-type:"+self.mimeType[os.path.splitext(requestUrl)[1]]+";charset=utf-8\r\n\r\n").encode(encoding="utf8")+con)
                    clientTcp.close()

                else:
                    clientTcp.send(b"HTTP/1.1 404 not find")
                    clientTcp.close()
        else:
            # 用户发起请求
            self.route_handle(requestData,clientTcp)

    def client_handle(self,clientTcp,clientInfo):
        '''多线程处理客户端的请求'''
        requestData=clientTcp.recv( self.recvNum)

        # 对每一个请求做处理的的时候，获得请求的信息，并且格式化
        # 实现具体的http协议

        self.request_handle(self.requestData_handle(requestData),clientTcp)

    def createTcp(self):
        '''创建tcp服务器'''
        socketTcp=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        socketTcp.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        socketTcp.bind((self.host,self.port))
        socketTcp.listen(self.listen)
        while True:
            clientTcp,clientInfo=socketTcp.accept()
            threading.Thread(target=self.client_handle,args=(clientTcp,clientInfo)).start()

    def start(self,host="",port=8888,listen=512):
        '''启动函数'''
        self.host=host
        self.port=port
        self.listen=listen
        self.createTcp()



app=server()

@app.route("/a/:id",methods=["GET"])
def aa(req,res):

    id=int(req["params"]["id"])
    data=[
        {"id":"1","name":"zhangsan"},
        {"id":"2","name":"lisi"},
        {"id":"3","name":"wangwu"},
    ]
    print(data[id])

    return render_template(app.template_dir+"/1.html",data[id])


@app.route("/b/:abc",methods=["GET"])
def bb(req,res):

    return req["query"]["name"]
app.start()
