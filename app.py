import os
import apiai
import json
import requests
import random

from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)

ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
SECRET = os.environ.get('SECRET')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
DIALOGFLOW_CLIENT_ACCESS_TOKEN = os.environ.get('DIALOGFLOW_CLIENT_ACCESS_TOKEN')
CX = os.environ.get('CX')

ai = apiai.ApiAI(DIALOGFLOW_CLIENT_ACCESS_TOKEN)
line_bot_api = LineBotApi(ACCESS_TOKEN)
handler = WebhookHandler(SECRET)

@app.route('/')
def index():
    return "<p>Success</p>"


# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# ================= 客製區 Start =================
def is_alphabet(uchar):
    if '\u4e00' <= uchar<='\u9fff':
        print('Chinese')
        return "zh-tw"
    else:
        return "en"
# ================= 客製區 End =================

# ================= 機器人區塊 Start =================
@handler.add(MessageEvent, message=TextMessage)  # default
def handle_text_message(event):                  # default
    msg = event.message.text # message from user
    uid = event.source.user_id # user id
    # 1. 傳送使用者輸入到 dialogflow 上
    ai_request = ai.text_request()
    #ai_request.lang = "zh-tw"
    ai_request.lang = is_alphabet(msg)
    ai_request.session_id = uid
    ai_request.query = msg

    # 2. 獲得使用者的意圖
    ai_response = json.loads(ai_request.getresponse().read())
    user_intent = ai_response['result']['metadata']['intentName']

    # 3. 根據使用者的意圖做相對應的回答
    thumbnail_image_url="https://img.88tph.com/production/20180121/12476547-1.jpg!/watermark/url/L3BhdGgvbG9nby5wbmc/align/center"
    if user_intent == "what to eat": # 使用者詢問
        # 建立一個 button 的 template
        buttons_template_message = TemplateSendMessage(
            alt_text="你現在在哪?",
            template=ButtonsTemplate(
                thumbnail_image_url=thumbnail_image_url,
                title="你現在在哪?",
                text="傳送位置給我吧",
                actions=[
                    URITemplateAction(
                        label="告訴我你的位置",
                        uri="line://nv/location"
                    )
                ]
            )
        )
        line_bot_api.reply_message(
            event.reply_token,
            buttons_template_message)
    elif user_intent == "Default Welcome Intent": # 歡迎使用
        msg = "肚子餓了嗎?你想吃什麼"
        buttons_template_message = TemplateSendMessage(
            alt_text="你現在在哪?",
            template=ButtonsTemplate(
                thumbnail_image_url=thumbnail_image_url,
                title="你現在在哪?",
                text="傳送位置給我吧",
                actions=[
                    URITemplateAction(
                        label="告訴我你的位置",
                        uri="line://nv/location"
                    )
                ]
            )
        )
        line_bot_api.reply_message(
            event.reply_token,
            [TextSendMessage(text=msg), buttons_template_message])
    elif user_intent == "goodbye": # 結束對話
        msg = "下次要再問我唷~"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=msg))
    else: # 聽不懂時的回答
        msg = "我聽不懂QAQ"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=msg))


@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    # 獲取使用者的經緯度
    lat = event.message.latitude
    lng = event.message.longitude
    
    # 使用 Google API Start =========
    # 1. 搜尋附近餐廳
    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?key={}&location={},{}&rankby=distance&type=restaurant&language=zh-TW".format(GOOGLE_API_KEY, lat, lng)
    nearby_results = requests.get(nearby_url)
    
    # 2. 得到最近的20間餐廳
    nearby_restaurants_dict = nearby_results.json()
    top20_restaurants = nearby_restaurants_dict["results"]
    ## CUSTOMe choose rate >= 4
    res_num = (len(top20_restaurants)) ##20
    above4 = []
    for i in range(res_num):
        try:
            if top20_restaurants[i]['rating'] > 3.9:
                #print('rate: ', top20_restaurants[i]['rating'])
                above4.append(i)
        except:
            KeyError

    # 3. 隨機選擇一間餐廳
    restaurant = random.choice(top20_restaurants)
    ab4_num = len(above4)
    columns = []
    if ab4_num <= 0:
        print('no 4 star resturant found')
        msg = "附近沒有評分大於四的餐廳"
        # 4. 檢查餐廳有沒有照片，有的話會顯示
        if restaurant.get("photos") is None:
            thumbnail_image_url = "https://cdn.shopify.com/s/files/1/1285/0147/products/sign2-032a.png?v=1527227219"
        else:
            # 根據文件，最多只會有一張照片
            photo_reference = restaurant["photos"][0]["photo_reference"]
            thumbnail_image_url = "https://maps.googleapis.com/maps/api/place/photo?key={}&photoreference={}&maxwidth=1024".format(GOOGLE_API_KEY, photo_reference)
        
        # 5. 組裝餐廳詳細資訊
        rating = "無" if restaurant.get("rating") is None else restaurant["rating"]
        address = "沒有資料" if restaurant.get("vicinity") is None else restaurant["vicinity"]
        opening = "沒有資料" if restaurant.get("opening_hours") is None else restaurant["opening_hours"]["open_now"]
        if opening == False:
            opening = "休息中"
        elif opening == True:
            opening = "營業中"
        details = "評分：{}\n地址：{}\n現在營業；{}".format(rating, address, opening)

        # 6. 取得餐廳的 Google map 網址
        map_url = "https://www.google.com/maps/search/?api=1&query={lat},{lng}&query_place_id={place_id}".format(
            lat=restaurant["geometry"]["location"]["lat"],
            lng=restaurant["geometry"]["location"]["lng"],
            place_id=restaurant["place_id"]
        )
        # 7. 取得菜單網址
        menu = "菜單"
        image_url = "https://www.googleapis.com/customsearch/v1?key={}&cx={}&num=1&alt=json&q={q}&searchType=image".format(
            GOOGLE_API_KEY, CX,
            q=restaurant["name"]+menu
        )
        image_results = requests.get(image_url)
        image_json = image_results.json()
        image = image_json["items"][0]["link"]
        # 回覆使用 Buttons Template
        buttons_template_message = TemplateSendMessage(
            alt_text=restaurant["name"],
            template=ButtonsTemplate(
                thumbnail_image_url=thumbnail_image_url,
                title=restaurant["name"],
                text=details,
                actions=[
                    URITemplateAction(
                        label='查看地圖',
                        uri=map_url
                    ),
                    URITemplateAction(
                        label='查看菜單',
                        uri=image
                    )
                ]
            )
        )
        line_bot_api.reply_message(
            event.reply_token,
            [TextSendMessage(text=msg), buttons_template_message])
    else:
        print(ab4_num)
        for i in range(ab4_num):
            if i == 10:
                print("break")
                break
            restaurant = top20_restaurants[above4[i]]
            # 4. 檢查餐廳有沒有照片，有的話會顯示
            if restaurant.get("photos") is None:
                thumbnail_image_url = "https://cdn.shopify.com/s/files/1/1285/0147/products/sign2-032a.png?v=1527227219"
            else:
                # 根據文件，最多只會有一張照片
                photo_reference = restaurant["photos"][0]["photo_reference"]
                thumbnail_image_url = "https://maps.googleapis.com/maps/api/place/photo?key={}&photoreference={}&maxwidth=1024".format(GOOGLE_API_KEY, photo_reference)
            
            # 5. 組裝餐廳詳細資訊
            rating = "無" if restaurant.get("rating") is None else restaurant["rating"]
            address = "沒有資料" if restaurant.get("vicinity") is None else restaurant["vicinity"]
            opening = "沒有資料" if restaurant.get("opening_hours") is None else restaurant["opening_hours"]["open_now"]
            if opening == False:
                opening = "休息中"
            elif opening == True:
                opening = "營業中"
            details = "評分：{}\n地址：{}\n現在營業：{}".format(rating, address, opening)
            print(details)

            # 6. 取得餐廳的 Google map 網址
            map_url = "https://www.google.com/maps/search/?api=1&query={lat},{lng}&query_place_id={place_id}".format(
                lat=restaurant["geometry"]["location"]["lat"],
                lng=restaurant["geometry"]["location"]["lng"],
                place_id=restaurant["place_id"]
            )
            # 7. 取得菜單網址
            menu = "菜單"
            image_url = "https://www.googleapis.com/customsearch/v1?key={}&cx={}&num=1&alt=json&q={q}&searchType=image".format(
                GOOGLE_API_KEY, CX,
                q=restaurant["name"]+menu
            )
            image_results = requests.get(image_url)
            image_json = image_results.json()
            image = image_json["items"][0]["link"]
            print(restaurant["name"])
            print(image)
            columns.append(
                CarouselColumn(
                    thumbnail_image_url=thumbnail_image_url,
                    title=restaurant["name"],
                    text=details,
                    actions=[
                        URITemplateAction(
                            label='查看地圖',
                            uri=map_url
                        ),
                        URITemplateAction(
                            label='查看菜單',
                            uri=image
                        )
                    ]
                )
            )
    # 使用 Google API End =========

    # 回覆使用 Carousel Template
    carousel_template_message = TemplateSendMessage(
        alt_text="評分四以上餐廳",
        template=CarouselTemplate(
            columns
        )
    )
    line_bot_api.reply_message(
        event.reply_token,
        carousel_template_message)
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)