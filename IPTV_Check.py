# -*- coding: UTF-8 -*-
import os
import re
import json
import time
import shutil
import traceback
from datetime import datetime
from subprocess import PIPE

from ffmpy import FFprobe
from func_timeout import func_set_timeout, FunctionTimedOut

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
def get_stream(num, csvRowArry, url):
    try:
        ffprobe = FFprobe(
            inputs={url: ' -v error -show_format -show_streams -print_format json'})
        cdata = json.loads(ffprobe.run(
            stdout=PIPE, stderr=PIPE)[0].decode('utf-8'))
        return cdata
    except Exception as e:
        # traceback.print_exc()
        print('{},{},{}'.format('ffprobe返回异常', csvRowArry[0], csvRowArry[1]))
        return False


def check_channel(csvRowArray, taskNum):
    iptvUrl = csvRowArray[1]
    try:
        video_metaData = get_stream(taskNum, csvRowArray, iptvUrl)
        if video_metaData:
            flagAudio = 0
            flagVideo = 0
            codec_name = ''
            flagHDR = 0
            width = 0
            height = 0
            bitRate = 2048
            frameRate = 25
            for i in video_metaData['streams']:
                if i['codec_type'] == 'video':
                    flagVideo = 1
                    codec_name = i['codec_name'].upper()
                    # codec_name = codec_name.upper()
                    if 'color_space' in i:
                        # https://www.reddit.com/r/ffmpeg/comments/kjwxm9/how_to_detect_if_video_is_hdr_or_sdr_batch_script/
                        if 'bt2020' in i['color_space']:
                            flagHDR = 1
                    if 'coded_width' in i:  # 取最高分辨率
                        width = i['coded_width']
                        height = i['coded_height']
                    if i['avg_frame_rate'] == '25/1':
                        frameRate = '25fps'
                    if i['avg_frame_rate'] == '50/1':
                        frameRate = '50fps'
                    if 'tags' in i:
                        bitRate = i['tags']['variant_bitrate']
                        if bitRate.isdigit():
                           bitRate = int(bitRate) / width / height
                           bitRate = round(bitRate, 2)
                        else:
                            bitRate = 2048
                elif i['codec_type'] == 'audio':
                    flagAudio = 1
            if flagAudio == 0:
                print('[{}] {}({}) Error: Video Only!'.format(
                    str(taskNum), csvRowArray[0], csvRowArray[1]))
                return False
            if flagVideo == 0:
                print('[{}] {}({}) Error: Audio Only!'.format(
                    str(taskNum), csvRowArray[0], csvRowArray[1]))
                return False
            if (width == 0) or (height == 0):
                print('[{}] {}({}) Error: {}x{}'.format(
                    str(taskNum), csvRowArray[0], csvRowArray[1], width, height))

            if flagHDR == 0:
                # 编号，分辨率，帧率，码率,编码格式，名称，url
                print('[{}] {}*{},{},{},{},{},{}'.format(str(taskNum), width, height, codec_name, frameRate, bitRate,
                                                         csvRowArray[0], csvRowArray[1]))
                return [width, height, codec_name, frameRate, bitRate]
            if flagHDR == 1:
                print(
                    '[{}] {}*{},{},{},(HDR),{},{}'.format(str(taskNum), width, height, frameRate, bitRate,
                                                                  csvRowArray[0], csvRowArray[1]))
                return [width, height, codec_name+'(HDR)', frameRate, bitRate]
        else:
            return False

    except Exception as e:
        # 通过，写入
        with open('checked_error.txt', 'a+', encoding="utf-8") as f1:
            # 名称，URL
            print('{},{}'.format(csvRowArray[0], csvRowArray[1]), file=f1)
            # traceback.print_exc()
        return False


def print_info():
    print('Time: {}-{}-{} {}:{}'.format(dt.year, dt.month, dt.day, dt.hour, dt.minute))


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
    num = 1
    for line3 in all_lines:
        # print line3
        dataRow = line3.replace("\n", "").replace("\r", "").split(",")
        try:
            if dataRow[1] in uniqueList:
                ret = False
            else:
                uniqueList.append(dataRow[1])
                ret = check_channel(dataRow, num)
        except FunctionTimedOut as e:
            # traceback.print_exc()
            print('[{}] {}({}) Error:{}'.format(
                str(num), dataRow[0], dataRow[1], str(e)))
            ret = False
        if (ret):
            # 通过，写入
            with open('checked{}.txt'.format(times), 'a+', encoding="utf-8") as f1:
                # 编号，名称，分辨率，(HDR|HEVC|H264),帧率，URL
                print('[{}],{}x{},{},{},{},{},{}'.format(num, ret[0], ret[1], ret[2], ret[3], ret[4],
                                                       dataRow[0],dataRow[1]), file=f1)
            total = total + 1
        num = num + 1
        time.sleep(0.25)

    print('Total: {}'.format(total))


if __name__ == '__main__':
    main()
