### 介绍
IPTV.m3u和IPTV.txt都是移动IPTV直播源（请勿商用！），推荐 IPTV.m3u 和 Tivimate（或者Perfect Player、Televizo）搭配使用，体验非常好。（IPTV.txt可以配置到tvtbox等类似软件使用）。
以下是免翻墙链接，任选一个即可：
https://cdn.jsdelivr.net/gh/yue365/IPTV@master/IPTV.m3u
https://fastly.jsdelivr.net/gh/yue365/IPTV@master/IPTV.m3u
https://mirror.ghproxy.com/raw.githubusercontent.com/yue365/IPTV/master/IPTV.m3u

TVBox EPG接口：https://epg.11416.xyz/?ch={name}&date={date}

### 直播源检测
IPTV_Checker.py 可以批量检测直播源视频分辨率、帧率、编码格式、音频信息等，虽然有的直播源可以被检测到动态比特率（但这个值不准确）也就是俗称的码率，但仍有大部分 HEVC + AAC 组合的直播源始终无法检测其画质优劣，欢迎各位喜欢折腾的朋友提供思路（如何检测视频码率，音频码率？以便在众多直播源里优中选优）

### 感谢：wcb1969、SPX372928、fanmingming、Meroser

### 我的直播源库
<img src="https://github.com/yue365/IPTV/blob/master/IPTV_data.png"/>
