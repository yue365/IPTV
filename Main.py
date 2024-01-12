import csv
import sys
import json
import os
import re
import traceback
import requests
import subprocess
import time
import shutil
from ffmpy import FFprobe
from subprocess import PIPE
from sys import stdout
from termcolor import colored, RESET
from datetime import datetime
from func_timeout import func_set_timeout, FunctionTimedOut
from requests.adapters import HTTPAdapter

dt = datetime.now()
# Channel	Group	Source	Link    Description
# Description 应当对该源的已知参数进行标注（如码率，HDR）

SKIP_FFPROBE_MESSAGES = [re.compile(pattern) for pattern in (
    'Last message repeated',
    'mmco: unref short failure',
    'number of reference frames .+ exceeds max',
)]

uniqueList = []


@func_set_timeout(18)
def get_stream(num, clist, uri):
    try:
        ffprobe = FFprobe(
            inputs={uri: ' -v error -show_format -show_streams -print_format json'})
        cdata = json.loads(ffprobe.run(
            stdout=PIPE, stderr=PIPE)[0].decode('utf-8'))
        return cdata
    except Exception as e:
        # traceback.print_exc()
        print('{},{},{}'.format('ffprobe返回异常', clist[0], clist[1]))
        return False


def check_channel(csvRow, num):
    # clist 为一行 csv
    iptv_url = csvRow[1]
    # requests.adapters.DEFAULT_RETRIES = 3
    try:
        video_metaData = get_stream(num, csvRow, iptv_url)
        if video_metaData:
            flagAudio = 0
            flagVideo = 0
            flagHEVC = 0
            flagHDR = 0
            vheight = 0
            vwidth = 0
            frameRate = 25
            for i in video_metaData['streams']:
                if i['codec_type'] == 'video':
                    flagVideo = 1
                    if 'color_space' in i:
                        # https://www.reddit.com/r/ffmpeg/comments/kjwxm9/how_to_detect_if_video_is_hdr_or_sdr_batch_script/
                        if 'bt2020' in i['color_space']:
                            flagHDR = 1
                    if i['codec_name'] == 'hevc':
                        flagHEVC = 1
                    if vwidth <= i['coded_width']:  # 取最高分辨率
                        vwidth = i['coded_width']
                        vheight = i['coded_height']
                    if i['avg_frame_rate'] == '25/1':
                        frameRate = '25FPS';
                    if i['avg_frame_rate'] == '50/1':
                        frameRate = '50FPS';
                elif i['codec_type'] == 'audio':
                    flagAudio = 1
            if flagAudio == 0:
                print('[{}] {}({}) Error: Video Only!'.format(
                    str(num), csvRow[0], csvRow[1]))
                return False
            if flagVideo == 0:
                print('[{}] {}({}) Error: Audio Only!'.format(
                    str(num), csvRow[0], csvRow[1]))
                return False
            if (vwidth == 0) or (vheight == 0):
                print('[{}] {}({}) Error: {}x{}'.format(
                    str(num), csvRow[0], csvRow[1], vwidth, vheight))

            if flagHDR == 0:
                # 编号，名称，分辨率，帧率，url
                print('[{}],{},{}*{},{},{}'.format(str(num), csvRow[0], vwidth, vheight, frameRate, csvRow[1]))
                # print(csvRow[1])
                return [vwidth, vheight, "H264", frameRate]
            if flagHDR == 1:
                print(
                    '[{}] {}({}),分辨率:{}*{},(HDR Enabled),帧率:{}'.format(str(num), csvRow[0], csvRow[1], vwidth, vheight,
                                                                       frameRate))
                return [vwidth, vheight, 'HDR', frameRate]
            if flagHEVC == 1:  # https://news.ycombinator.com/item?id=19389496  默认有HDR的算HEVC
                print(
                    '[{}] {}({}),分辨率:{}*{},(HEVC Enabled),帧率:{}'.format(str(num), csvRow[0], csvRow[1], vwidth, vheight,
                                                                        frameRate))
                return [vwidth, vheight, 'HEVC', frameRate]
        else:
            return False

    except Exception as e:
        # 通过，写入
        with open('checked_error.txt', 'a+', encoding="utf-8") as f1:
            # 名称，URL
            print('{},{}'.format(csvRow[0], csvRow[1]), file=f1)
        return False


def print_info():
    print('Time: {}-{}-{} {}:{}'.format(dt.year,
                                        dt.month, dt.day, dt.hour, dt.minute))
    # subprocess.run(['ffprobe'])


def rm_files(target, selection):
    if selection == 1:  # 删目录
        try:
            shutil.rmtree(target)
        except OSError:
            pass
        try:
            os.mkdir(target)
        except OSError:
            pass
    else:  # 删文件
        try:
            os.remove(target)
        except OSError:
            pass


def getdes(st):  # 不是所有的源都有描述
    if st:
        return '[{}]'.format(st)
    else:
        return ''


def main():
    print_info()
    total = 0
    fulltimes = '-{}{}{}{}{}'.format(dt.year, dt.month, dt.day, dt.hour, dt.minute)  # 时间后缀
    # times = fulltimes # 有时间后缀
    times = ''  # 无时间后缀

    # 清空旧文件
    rm_files('checked.txt', 2)
    rm_files('checked_error.txt', 2)
    # read txt method three
    f2 = open("playlist.txt", "r", encoding="UTF-8")
    all_lines = f2.readlines()
    num = 1;
    for line3 in all_lines:
        # print line3
        data_row = line3.replace("\n", "").replace("\r", "").split(",")
        try:
            if data_row[1] in uniqueList:
                ret = False
            else:
                uniqueList.append(data_row[1])
                ret = check_channel(data_row, num)
        except FunctionTimedOut as e:
            # traceback.print_exc()
            print('[{}] {}({}) Error:{}'.format(
                str(num), data_row[0], data_row[1], str(e)))
            ret = False
        if (ret):
            # 通过，写入
            with open('checked{}.txt'.format(times), 'a+', encoding="utf-8") as f1:
                # 编号，名称，分辨率，(HDR|HEVC|H264),帧率，URL
                print('{},{},{}*{},{},{},{}'.format(num, data_row[0], ret[0], ret[1], ret[2], ret[3],
                                                  data_row[1]), file=f1)
            total = total + 1
        num = num + 1
        time.sleep(0.25)

    print('Total: {}'.format(total))


if __name__ == '__main__':
    main()
