#!/usr/bin/env python3

import httplib2
import os
import sys

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

import pprint
import json
import datetime
import subprocess
import urllib.error
import urllib.request
import re

#youtube data apiのoauth2認証キーのパス
CLIENT_SECRETS_FILE = "client_secrets.json"

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google API Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets



# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

%s

with information from the API Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                CLIENT_SECRETS_FILE))

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account.
YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
message=MISSING_CLIENT_SECRETS_MESSAGE,
scope=YOUTUBE_READ_WRITE_SCOPE)

storage = Storage("%s-oauth2.json" % sys.argv[0])
credentials = storage.get()

if credentials is None or credentials.invalid:
    flags = argparser.parse_args()
    credentials = run_flow(flow, storage, flags)

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
http=credentials.authorize(httplib2.Http()))

#それぞれのファイルのパス
#上から動画を保存するパス、サムネを保存するパス、辞書ファイルを保存するパス
movieFile = './downloaded'
photoFile = './thumbnails'
indexFile = './index.json'

def indexWriter():
    nextPage = ""
    dic = {}
    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId="LL",
            maxResults=10,
            pageToken=nextPage
        )
        response = request.execute()

        for snippet in response['items']:
            snippet = snippet['snippet']
            try:
                #if snippet['title'] == 'Private video' or snippet['title'] == 'Deleted video':
                    #continue;
                title = snippet['title']
                description = snippet['description']
                for i in snippet['thumbnails']:
                    #数あるサムネイルの中から最高画質(配列の一番後ろのやつ)を選択するためのfor文
                    pass
                thumbnail = snippet['thumbnails'][i]['url']
                videoId = snippet['resourceId']['videoId']
                channelName = snippet['videoOwnerChannelTitle']
                channelId = snippet['videoOwnerChannelId']
                publishDate = snippet['publishedAt']
            except:
                print(videoId+'を取得出来ませんでした。')
                continue;
            values = {videoId:{'title':title, 'description':description, 'thumbnail':thumbnail, 'channelName':channelName, 'channelId':channelId, 'publishedDate':publishDate}} 
            dic.update(values)
        try:
            nextPage = response['nextPageToken']
        except:
            break;
    #辞書ファイルが既に存在する場合、それに追加する形で保存する
    if os.path.exists(indexFile):
        readtf = open(indexFile, "r")
        read = json.load(readtf)
        dic.update(read)
    tf = open(indexFile, "w")
    json.dump(dic, tf)
    tf.close()
    print('辞書ファイル出力完了')

def downloader():
    if not os.path.exists(movieFile):
        print("動画保存先ファイルが存在しないので、作成します。")
        os.mkdir(movieFile)
    if not os.path.exists(photoFile):
        print("サムネイル保存先ファイルが存在しないので、作成します。")
        os.mkdir(photoFile)

    tf = open(indexFile, "r")
    dic = json.load(tf)
    fileList =  os.listdir(movieFile)
    for i in dic:
        if i+'.mp4' in fileList:
            print('ファイル名"'+i+'.mp4"は既に存在しているのでダウンロードを飛ばしました。')
            continue;
        url = 'https://www.youtube.com/watch?v='+i
        print(i+'をダウンロード中...')
        photoDownloader(dic[i]['thumbnail'], photoFile+'/'+i+'.jpg')
        #yt-dlpコマンドとそのオプション
        #ここをいじればダウンロードする画質とかを変えられる
        #これは1080p以下の最高画質か、最高画質をダウンロードするためのオプション
        values = ['./yt-dlp', '-P', movieFile, '-o', i, '-f', 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4][height<=1080] / bv*+ba/b', url]
        #values = ['./yt-dlp', '-P', movieFile, '-o', i, '-S', 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4][height<=1080]', url]
        check = subprocess.check_call(values)
        if check != 0:
            print(i+'のダウンロードに失敗しました')

def photoDownloader(url, dst_path):
    try:
        with urllib.request.urlopen(url) as web_file, open(dst_path, 'wb') as local_file:
            local_file.write(web_file.read())
    except urllib.error.URLError as e:
        print(e)

def nameChanger():
    for i in os.listdir(movieFile):
        m = re.match(r'.*\.mp4$', i)
        if m is None:
            #print(i)
            name = movieFile+'/'+i
            os.rename(name, name+'.mp4')

def manageDownloaded():
    tf = open(indexFile, "r")
    dic = json.load(tf)
    fileList =  os.listdir(movieFile)
    toRemove = [] 
    for i in dic:
        if i+'.mp4' not in fileList:
            print(i+'.mp4はダウンロード出来なかったので、辞書ファイルから削除します。')
            toRemove.append(i)
    for c in toRemove:
        dic.pop(c)
    tf = open(indexFile, "w")
    json.dump(dic, tf)
    tf.close()

def unliker():
    pass

if __name__ == "__main__":
    #youtubeApiから高評価した動画を全て読み出し、それらをjsonファイルに出力する
    indexWriter()
    #出力された辞書ファイルを元に動画とサムネイルをダウンロードする
    downloader()
    #ダウンロードされたファイルに何故か拡張子が付いていないものが含まれているので、.mp4と追加する
    nameChanger()
    #辞書に含まれているがダウンロードされなかったものを辞書から削除する
    manageDownloaded()
    #ダウンロード出来なかったもの(削除されたか非公開か)の高評価を解除する(未実装)
    unliker()
