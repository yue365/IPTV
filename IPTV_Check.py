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
def get_stream(num, playlist_row_arry, url):
    try:
        ffprobe = FFprobe(
            inputs={url: ' -v error -show_format -show_streams -print_format json'})
        cdata = json.loads(ffprobe.run(
            stdout=PIPE, stderr=PIPE)[0].decode('utf-8'))
        return cdata
    except Exception as e:
        # traceback.print_exc()
        # print('{},{},{}'.format('ffprobe返回异常', csvRowArry[0], csvRowArry[1]))
        with open('checked_error.txt', 'a+', encoding="utf-8") as f1:
            print('ffprobe返回异常,{},{}'.format(playlist_row_arry[0], playlist_row_arry[1]), file=f1)
        return False


def check_channel(playlist_row_arr, taskNum):
    iptvUrl = playlist_row_arr[1]
    try:
        video_metaData = get_stream(taskNum, playlist_row_arr, iptvUrl)
        if video_metaData:
            # 视频信息
            hdr_flag = 0
            audio_flag = 0
            video_flag = 0
            codec_name = ''
            width = 0
            height = 0
            frame_rate = 25
            video_bit_rate = 2048
            # 音频信息
            audio_bit_rate = ''
            audio_sample_rate = ''
            audio_channels = ''
            channel_layout = 'stereo'
            if len(video_metaData['streams']) > 0:
                for i in video_metaData['streams']:
                    if i['codec_type'] == 'video':
                        video_flag = 1
                        codec_name = i['codec_name'].upper()
                        # https://www.reddit.com/r/ffmpeg/comments/kjwxm9/how_to_detect_if_video_is_hdr_or_sdr_batch_script/
                        if 'color_space' in i:
                            if 'bt2020' in i['color_space']:
                                hdr_flag = 1
                        if 'coded_width' in i:  # 取最高分辨率
                            width = i['width']
                            height = i['height']
                        if i['avg_frame_rate'] == '25/1':
                            frame_rate = '25fps'
                        if i['avg_frame_rate'] == '50/1':
                            frame_rate = '50fps'
                        # if 'tags' in i:
                        #     bitRate = i['tags']['variant_bitrate']
                        #     if bitRate.isdigit():
                        #         bitRate = int(bitRate) / width / height
                        #         bitRate = round(bitRate, 2)
                        #     else:
                        #         bitRate = 2048
                    if i['codec_type'] == 'audio':
                        audio_flag = 1
                        if 'channels' in i:
                            audio_channels = i['channels']
                        if 'channel_layout' in i:
                            channel_layout = i['channel_layout']
                        if 'bit_rate' in i:
                            audio_bit_rate = i['bit_rate']
                        if 'sample_rate' in i:
                            audio_sample_rate = i['sample_rate']
            if audio_flag == 0:
                print('[{}] {}({}) Error: Video Only!'.format(
                    taskNum, playlist_row_arr[0], playlist_row_arr[1]))
                return False
            if video_flag == 0:
                print('[{}] {}({}) Error: Audio Only!'.format(
                    taskNum, playlist_row_arr[0], playlist_row_arr[1]))
                return False
            if (width == 0) or (height == 0):
                print('[{}] {}({}) Error: {}x{}'.format(
                    taskNum, playlist_row_arr[0], playlist_row_arr[1], width, height))

            if hdr_flag == 0:
                print('[{}],分辨率:{}*{},视频编码:{},帧率:{},比特率:{},声道数:{},声道类型:{},声音采样率:{},声音比特率:{},{},{}'.format(
                    taskNum, width, height, codec_name, frame_rate, video_bit_rate,
                    audio_channels, channel_layout, audio_sample_rate, audio_bit_rate,
                    playlist_row_arr[0], playlist_row_arr[1]))

                return [width, height, codec_name, frame_rate, video_bit_rate, audio_channels,
                        channel_layout, audio_sample_rate, audio_bit_rate]
            if hdr_flag == 1:
                codec_name = codec_name + '(HDR)'
                print('[{}],分辨率:{}*{},视频编码:{},帧率:{},比特率:{},声道数:{},声道类型:{},声音采样率:{},声音比特率:{},{},{}'.format(
                    taskNum, width, height, codec_name, frame_rate, video_bit_rate, audio_channels, channel_layout,
                    audio_sample_rate, audio_bit_rate, playlist_row_arr[0], playlist_row_arr[1]))

                return [width, height, codec_name, frame_rate, video_bit_rate, audio_channels,
                        channel_layout, audio_sample_rate, audio_bit_rate]
            else:
                return False
        else:
            return False
    except Exception as e:
        # 通过，写入
        # with open('checked_error.txt', 'a+', encoding="utf-8") as f1:
        #     # 名称，URL
        #     print('{},{}'.format(csvRowArray[0], csvRowArray[1]), file=f1)
        traceback.print_exc()
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
                res = False
            else:
                uniqueList.append(dataRow[1])
                res = check_channel(dataRow, num)
        except FunctionTimedOut as e:
            # traceback.print_exc()
            print('[{}] {}({}) Error:{}'.format(
                str(num), dataRow[0], dataRow[1], str(e)))
            res = False
        if (res):
            # 通过，写入
            with open('checked{}.txt'.format(times), 'a+', encoding="utf-8") as f1:
                # 编号，名称，分辨率，(HDR|HEVC|H264),帧率，声道数，声道类型，声音采样率，声音比特率，URL
                print('[{}],分辨率:{}*{},视频编码:{},帧率:{},比特率:{},声道数:{},声道类型:{},声音采样率:{},声音比特率:{},{},{}'.format(
                    num, res[0], res[1], res[2], res[3], res[4], res[5], res[6], res[7], res[8],
                    dataRow[0], dataRow[1]), file=f1)
            total = total + 1
        num = num + 1
        time.sleep(0.25)

    print('Total: {}'.format(total))


if __name__ == '__main__':
    main()
