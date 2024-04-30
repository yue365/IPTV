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

SKIP_FFPROBE_MESSAGES = [re.compile(pattern) for pattern in (
    'Last message repeated',
    'mmco: unref short failure',
    'number of reference frames .+ exceeds max',
)]

uniqueList = []


def print_start_time():
    print('任务开始时间: {}-{}-{} {}:{}:{}'.format(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second))


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
        print('[{}],ffprobe返回异常,{},{}'.format(str(num), playlist_row_arry[0], playlist_row_arry[1]))

        with open('checked_error.txt', 'a+', encoding="utf-8") as f1:
            print('ffprobe返回异常,{},{}'.format(playlist_row_arry[0], playlist_row_arry[1]), file=f1)
        return False


def check_channel(playlist_row_arr, task_num):
    try:
        start_time = time.time()
        video_meta_data = get_stream(task_num, playlist_row_arr, playlist_row_arr[1])
        if video_meta_data:
            response_time = ((time.time() - start_time) * 1000)
            response_time = int(response_time)
            # 视频信息
            hdr_flag = 0
            audio_flag = 0
            video_flag = 0
            codec_name = ''
            width = 0
            height = 0
            frame_rate = 25
            video_bit_rate = '0'
            # 音频信息
            audio_codec_name = ''
            audio_bit_rate = '0'
            audio_sample_rate = ''
            audio_channels = ''
            channel_layout = 'stereo'
            if len(video_meta_data['streams']) > 0:
                for i in video_meta_data['streams']:
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
                        # video_bit_rate = i['tags']['variant_bitrate']
                        # if video_bit_rate.isdigit():
                        #     video_bit_rate = int(video_bit_rate) / 1024 / 8
                        #     video_bit_rate = round(video_bit_rate, 2)

                    if i['codec_type'] == 'audio':
                        audio_flag = 1
                        audio_codec_name = i['codec_name'].upper()
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
                    task_num, playlist_row_arr[0], playlist_row_arr[1]))
                return False
            if video_flag == 0:
                print('[{}] {}({}) Error: Audio Only!'.format(
                    task_num, playlist_row_arr[0], playlist_row_arr[1]))
                return False
            if (width == 0) or (height == 0):
                print('[{}] {}({}) Error: {}x{}'.format(
                    task_num, playlist_row_arr[0], playlist_row_arr[1], width, height))

            if hdr_flag == 0:
                print('[{}],分辨率:{}*{},视频编码:{},帧率:{},比特率:{},声音编码:{},声道数:{},声道类型:{},'
                      '声音采样率:{},声音比特率:{},响应时间:{},{},{}'.format(
                    task_num, width, height, codec_name, frame_rate, video_bit_rate, audio_codec_name,
                    audio_channels, channel_layout, audio_sample_rate, audio_bit_rate,
                    response_time, playlist_row_arr[0], playlist_row_arr[1]))

                return [width, height, codec_name, frame_rate, video_bit_rate, audio_codec_name, audio_channels,
                        channel_layout, audio_sample_rate, audio_bit_rate, response_time]
            if hdr_flag == 1:
                codec_name = codec_name + '(HDR)'
                print('[{}],分辨率:{}*{},视频编码:{},帧率:{},比特率:{},声音编码:{},声道数:{},声道类型:{},'
                      '声音采样率:{},声音比特率:{},响应时间:{},{},{}'.format(
                    task_num, width, height, codec_name, frame_rate, video_bit_rate, audio_codec_name,
                    audio_channels, channel_layout, audio_sample_rate, audio_bit_rate,
                    response_time, playlist_row_arr[0], playlist_row_arr[1]))

                return [width, height, codec_name, frame_rate, video_bit_rate, audio_codec_name, audio_channels,
                        channel_layout, audio_sample_rate, audio_bit_rate, response_time]
            else:
                return False
        else:
            return False
    except Exception as e:
        # 通过，写入
        # with open('checked_error.txt', 'a+', encoding="utf-8") as f1:
        # 名称，URL
        print('check_channel函数中异常,{},{},{},'.format(task_num, playlist_row_arr[0], playlist_row_arr[1], str(e)))
        # traceback.print_exc()
        return False


def main():
    task_num = 1
    total_checked = 1
    fulltimes = '-{}{}{}{}{}'.format(dt.year, dt.month, dt.day, dt.hour, dt.minute)  # 时间后缀
    # times = fulltimes # 有时间后缀
    times = ''  # 无时间后缀

    # 清空旧文件
    rm_files('checked.txt', 2)
    rm_files('checked_error.txt', 2)
    # read txt method three
    playlist_file = open("playlist.txt", "r", encoding="UTF-8")
    all_lines = playlist_file.readlines()
    head_print_flag = 0

    for line3 in all_lines:
        row_array = line3.replace("\n", "").replace("\r", "").split(",")
        try:
            if row_array[1] in uniqueList:
                res = False
            else:
                uniqueList.append(row_array[1])
                res = check_channel(row_array, task_num)
        except FunctionTimedOut as e:
            # traceback.print_exc()
            # print('[{}] {}({}) Error:{}'.format(
            #     task_num, row_array[0], row_array[1], str(e)))
            with open('checked_error.txt', 'a+', encoding="utf-8") as f1:
                print('ffprobe返回异常,{},{}'.format(row_array[0], row_array[1]), file=f1)
            res = False
        if (res):
            if head_print_flag == 0:
                with open('checked{}.txt'.format(times), 'a+', encoding="utf-8") as f1:
                    print('序号,分辨率,视频编码,帧率,比特率(kbps),声音编码,声道数,声道类型,声音采样率(Hz),声音比特率(kbps),响应时间(ms),频道名称,频道URL', file=f1)
                    head_print_flag = 1
            # 通过，写入
            with open('checked{}.txt'.format(times), 'a+', encoding="utf-8") as f1:
                # 编号，名称，分辨率，(HDR|HEVC|H264),帧率，声道数，声道类型，声音采样率，声音比特率，URL
                print(
                    '[{}],{}*{},{},{},{},{},{},{},{},{},{},{},{}'.format(
                        task_num, res[0], res[1], res[2], res[3], res[4], res[5], res[6], res[7], res[8],
                        res[9], res[10], row_array[0], row_array[1]), file=f1)
                total_checked += 1
        task_num += 1
        time.sleep(0.25)
    print('Total: {}'.format(total_checked))


if __name__ == '__main__':
    print_start_time()
    main()
    print('任务结束时间: {}-{}-{} {}:{}:{}'.format(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second))
