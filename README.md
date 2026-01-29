**subscribe.py**

用paho.mqtt连接python和mqtt服务器

这一样就可以订阅mqtt上的数据，并采集下来供python进行一些解码以及可视化的操作（接下来的工作方向）

PS：记得将安全证书文件emqxsl-ca.crt加入同一文件夹

**frame_check_decode.py**

将4+8+1共13字节的hex格式数据帧解码（目前特定解码数据为车轮数据，identifier-0x0CFFC6EF）为具体信息

这样就可以真正读懂信息，接下来就可以做可视化界面了

PS:这个代码中用于测试输入的方式直接就是input()，因此处理对象是hex还是ASCII需要注意

（↑好像不用改——编完subscribe2decode.py后感）

**subscribe2decode.py**

直接连接mqtt，作为客户端接受数据然后处理，这中间传输的数据是hex

**subscribe2html.py (仅供参考！！！)**

使用ai做的尝试，试图将脚本分析的数据显示到html网页中

在实现了部分的车轮报文解码的基础上，通过flask库和websocket将脚本（websocket服务端）与网页（websocket客户端）连接

**scalable_static_py2html.py (仅供参考！！！)**

使用ai做的尝试，试图将html代码改成可以扩展的格式（不太成功，这一版html文件要做扩展依旧很复杂）

同时由于集成扩展功能时使用了Vue.js模板，与原先的flask jinja2渲染产生了冲突，ai遂废弃采用jinja2，转而将HTML改为纯静态。

