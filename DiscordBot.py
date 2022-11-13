import datetime
import os
from collections import deque, defaultdict

import discord
import requests
import youtube_dl
from discord import app_commands
from discord.ext import timers
from dotenv import load_dotenv
from pymongo import MongoClient

from hanspell import spell_checker

load_dotenv()
apikey = os.getenv('APIKEY')
blacklist = ['즘', '틱', '늄', '슘', '퓸', '늬', '뺌', '섯', '숍', '튼', '름', '늠', '쁨']
COLOR = 0x33CCFF


class Timer:
    @classmethod
    def calc(cls, time):
        arr_time = []
        if time[-1] == "뒤":
            time = time[:-1].strip()
            arr_time = time.split()
            date = datetime.datetime.now()
        else:
            date = datetime.datetime.now()
            arr_time = time.split()
            date -= datetime.timedelta(hours=date.hour, minutes=date.minute, seconds=date.second)
            print(date)
        for __time in arr_time:
            if __time[-1] == "초":
                date += datetime.timedelta(seconds=int(__time[:-1]))
            elif __time[-1] == "분":
                date += datetime.timedelta(minutes=int(__time[:-1]))
            elif __time[-2:] == "시간":
                date += datetime.timedelta(hours=int(__time[:-2]))
                print(1)
            elif __time[-1:] == "시":
                date += datetime.timedelta(hours=int(__time[:-1]))
                print(2)
        date -= datetime.timedelta(hours=9)
        return date


class Music:
    def __init__(self) -> None:
        self.__voiceClient = None
        self.playlist = deque()
        self.is_playing = False
        self.ydl_options = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',  # ipv6 addresses cause issues sometimes
            'force-ipv4': True,
            'cachedir': False
        }
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

    async def add(self, url):
        with youtube_dl.YoutubeDL(self.ydl_options) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['formats'][0]['url']
            self.playlist.append(
                {
                    "audio": await discord.FFmpegOpusAudio.from_probe(url2, **self.ffmpeg_options),
                    "name": info["title"],
                    "url": url
                })

    async def connect(self, voice_channel):
        if self.__voiceClient is None:
            self.__voiceClient: discord.VoiceClient = await voice_channel.connect()

    def play(self):
        if self.__voiceClient.is_paused():
            self.__voiceClient.resume()
        elif self.playlist:
            self.__voiceClient.play(self.playlist[0]["audio"], after=lambda e: self.play())
            self.playlist.popleft()

    def pause(self):
        self.__voiceClient.pause()

    def stop(self):
        self.__voiceClient.stop()


class Stock:
    def __init__(self, stock_name) -> None:
        stock = DB.get_stock(stock_name)
        self.stockName = stock["stockName"]
        self.price = stock["price"]

    def get_stock(self):
        return {
            "stockName": self.stockName,
            "price": self.price
        }


class StockUser:
    def __init__(self, username) -> None:
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["StockUser"]
        stock_user = db.find_one({"userName": username})
        self.userId = stock_user["userId"]
        self.userName = stock_user["userName"]
        self.money = stock_user["money"]
        self.rank = stock_user["rank"]
        self.stocks = defaultdict(int, stock_user["stocks"])
        print(self.stocks)


class StockGame:
    @classmethod
    def buy(cls, user: StockUser, stock: Stock, cnt: int):
        stock_user = StockUser(user.userName)
        stock_user.money -= stock.price * cnt
        stock_user.stocks[stock.stockName] += cnt
        DB.update_stock_user(stock_user)

    @classmethod
    def sell(cls, user: StockUser, stock: Stock, cnt: int):
        stock_user = StockUser(user.userName)
        stock_user.money += stock.price * cnt
        stock_user.stocks[stock.stockName] -= cnt
        DB.update_stock_user(stock_user)


class Room:
    def __init__(self, name) -> None:
        self.name = name
        self.is_playing = False
        self.user_list = []
        self.last_word = ""
        self.history = []
        self.last_user = name


rooms: [Room] = []


class EndTalk:
    @staticmethod
    def get_room(member: discord.Member) -> Room | None:
        for room in rooms:
            if member in room.user_list:
                return room
        return None

    # string list에서 단어, 품사와 같은 요소들을 추출할때 사용됩니다
    def midReturn(self, val, s, e):
        if s in val:
            val = val[val.find(s) + len(s):]
            if e in val:
                val = val[:val.find(e)]
        return val

    # string에서 XML 등의 요소를 분석할때 사용됩니다

    def midReturn_all(self, val: str, s, e) -> list:
        if s in val:
            tmp = val.split(s)
            arr = []
            for i in range(0, len(tmp)):
                if e in tmp[i]:
                    arr.append(tmp[i][:tmp[i].find(e)])
        else:
            arr = []
        return arr

    def checkexists(self, query):
        url = 'https://krdict.korean.go.kr/api/search?key=' + apikey + '&part=word&sort=popular&num=100&pos=1&q=' + query
        response = requests.get(url, verify=False)
        ans = ''
        words = self.midReturn_all(response.text, '<item>', '</item>')
        for w in words:
            word = self.midReturn(w, '<word>', '</word>')
            pos = self.midReturn(w, '<pos>', '</pos>')
            if len(word) > 1 and pos == '명사' and word == query:
                ans = w
        if len(ans) > 0:
            return self.midReturn(ans, '<word>', '</word>')
        else:
            return ''

    def checkword(self, query, room):
        result = self.checkexists(query)
        if query[0] == self.convert(room.last_word):
            print(self.convert(query[0]))
            room.last_word = self.convert(query[0])

        if len(result) > 0:
            if len(result) == 1:
                return "적어도 두 글자가 되어야 합니다"
            if result in room.history:
                return "이미 사용한 단어입니다."
            if result[len(result) - 1] in blacklist:
                return "아.. 좀 치사한데요.."
            if room.last_word != result[0] and room.last_word != "":
                return f"{room.last_word}(으)로 시작하는 단어를 입력해 주십시오."
            if room.user_list.index(room.last_user) + 1 == len(room.user_list):
                room.last_user = room.user_list[0]
            else:
                room.last_user = room.user_list[room.user_list.index(room.last_user) + 1]
            room.history.append(query)
            room.last_word = result[-1]
            if room.last_word == '':
                return f"{room.last_word}(으)로 시작하는 단어 {room.last_user}님 차례!"
            else:
                return f"{room.last_user}님 차례!"
        else:
            return ''

    def convert(self, rear):
        convertList = {"라": "나", "락": "낙", "란": "난", "랄": "날",
                       "람": "남", "랍": "납", "랏": "낫", "랑": "낭",
                       "략": "약", "량": "양", "렁": "넝", "려": "여",
                       "녀": "여", "력": "역", "녁": "역", "련": "연",
                       "년": "연", "렬": "열", "렴": "염", "념": "염",
                       "렵": "엽", "령": "영", "녕": "영", "로": "노",
                       "록": "녹", "론": "논", "롤": "놀", "롬": "놈",
                       "롭": "놉", "롯": "놋", "롱": "농", "료": "요",
                       "뇨": "요", "룡": "용", "뇽": "용", "루": "누",
                       "룩": "눅", "룬": "눈", "룰": "눌", "룸": "눔",
                       "룻": "눗", "룽": "눙", "류": "유", "뉴": "유",
                       "륙": "육", "률": "율", "르": "느", "륵": "늑",
                       "른": "는", "를": "늘", "름": "늠", "릅": "늡",
                       "릇": "늣", "릉": "능", "래": "내", "랙": "낵",
                       "랜": "낸", "랠": "낼", "램": "냄", "랩": "냅",
                       "랫": "냇", "랭": "냉", "례": "예", "뢰": "뇌",
                       "리": "이", "니": "이", "린": "인", "닌": "인",
                       "릴": "일", "닐": "일", "림": "임", "님": "임",
                       "립": "입", "닙": "입", "릿": "잇", "닛": "잇",
                       "링": "잉", "닝": "잉"}

        if rear in convertList:
            return convertList[rear]
        return rear


endtalk = EndTalk()


class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.synced = False
        self.music = Music()

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await tree.sync(guild=discord.Object(id=1038138701961769021))
            self.synced = True
        print(f"we have logged in as {self.user}.")

    async def on_member_join(self, member: discord.Member):
        DB.create_status_user(member=member)
        DB.create_stock_user(member=member)

    async def on_member_remove(self, member: discord.Member):
        DB.remove_status_user(member=member)
        DB.remove_stock_user(member=member)

    async def on_message(self, msg: discord.Message):
        if msg.author.bot:
            return
        for room in rooms:
            if room.is_playing and (msg.author == room.last_user):
                result = endtalk.checkword(msg.content, room)
                embed = discord.Embed(title="끝말잇기", color=COLOR)
                if result != '':
                    embed.add_field(name=f"{room.history[len(room.history) - 2]} > {room.history[-1]}", value=result,
                                    inline=False)
                    await msg.channel.send(embed=embed)
                else:
                    embed.add_field(name="없는 단어입니다.", value=f"{msg.author}님 다시 입력해주세요")
                    await msg.channel.send(embed=embed)
        if ChatManager.check_abuse(msg.content):
            await msg.channel.purge(limit=1)
            embed = discord.Embed(title="욕설 금지", color=COLOR)
            embed.add_field(name=f"{msg.author}님", value="욕설을 사용하시면 안되죠")
            await msg.channel.send(embed=embed)
            return
        # DB에 유저가 없으면 user.userName = None 
        user = Status(msg.author.name)
        if not user.userName:
            return
        user.add_exp(10)

    async def on_reminder(self, channel_id: int, author_id: int, text: str):
        channel = bot.get_channel(channel_id)
        user: discord.Member = channel.guild.get_member(author_id)
        now = datetime.datetime.now()
        embed = discord.Embed(color=COLOR)
        embed.add_field(name=f"현재 시각", value=f"{now.year}-{now.month}-{now.day} {now.hour}:{now.minute}:{now.second}",
                        inline=False)
        embed.add_field(name=f"메모 내용", value=f"{text}")
        await channel.send(embed=embed, content=f"{user.mention}님 알람입니다.")


bot = Bot()
tree = app_commands.CommandTree(bot)


class ChatManager():
    @classmethod
    def checkGrammer(cls, msg):
        return spell_checker.check(msg)

    @classmethod
    def check_abuse(cls, msg: str):
        api_url = os.getenv("NLP")
        headers = {
            "Authorization": os.getenv("MACHINE")}
        payload = {
            "inputs": f"{msg}",
            "options": {
                "wait_for_model": True
            }
        }
        response = requests.post(api_url, headers=headers, json=payload).json()
        print(response)
        if response[0][0]["label"] == "hate" and response[0][0]["score"] >= 0.7:
            return True
        return False


class Status:
    def __init__(self, username) -> None:
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["User"]
        user = db.find_one({"userName": username})
        if user:
            self.userId = user["userId"]
            self.userName = user["userName"]
            self.exp = user["exp"]
            self.level = user["level"]
            self.rank = user["rank"]
        else:
            self.userId = None
            self.userName = None
            self.exp = None
            self.level = None
            self.rank = None

    def get_status(self):
        return {
            "userId": self.userId,
            "userName": self.userName,
            "exp": self.exp,
            "level": self.level,
            "rank": self.rank
        }

    def add_exp(self, exp):
        self.exp += exp
        DB.update_user(self.get_status())

    def get_user(self):
        return DB.get_user(self.userName)


class DB:
    @classmethod
    def get_user(cls, username) -> dict | None:
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["User"]
        return db.find_one({"userName": username})

    @classmethod
    def update_user(cls, status: dict):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["User"]
        db.replace_one(
            {
                "userName": status["userName"]},
            {
                "userId": status["userId"],
                "userName": status["userName"],
                "exp": status["exp"],
                "level": status["level"],
                "rank": status["rank"]
            })

    @classmethod
    def create_status_user(cls, member: discord.Member):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["User"]
        db.insert_one({
            "userId": member.id,
            "userName": member.name,
            "exp": 0,
            "level": 0,
            "rank": 0
        })

    @classmethod
    def remove_status_user(cls, member: discord.Member):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["User"]
        db.delete_one({"userId": member.id})

    @classmethod
    def remove_stock_user(cls, member: discord.Member):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["StockUser"]
        db.delete_one({"userId": member.id})

    @classmethod
    def refresh_exp_ranking(cls):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["User"]
        users = []
        for post in db.find():
            users.append(
                {
                    "userId": post["userId"],
                    "userName": post["userName"],
                    "exp": post["exp"],
                    "level": post["level"],
                    "rank": post["rank"]
                })

        users.sort(key=lambda user: user["exp"], reverse=True)
        for rank, user in enumerate(users):
            user["rank"] = rank + 1
            db.replace_one({"userName": user["userName"]}, user)
        return True

    @classmethod
    def refresh_stock_user_ranking(cls):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["StockUser"]
        users = []
        for post in db.find():
            users.append(
                {
                    "uesrId": post["userId"],
                    "userName": post["userName"],
                    "money": post["money"],
                    "rank": post["rank"],
                    "stocks": post["stocks"]
                })

        users.sort(key=lambda user: user["money"], reverse=True)
        for rank, user in enumerate(users):
            user["rank"] = rank + 1
            db.replace_one({"userName": user["userName"]}, user)
        return True

    @classmethod
    def update_stock_user(cls, stock_user: StockUser):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["StockUser"]
        db.replace_one(
            {
                "userName": stock_user.userName},
            {
                "userId": stock_user.userId,
                "userName": stock_user.userName,
                "money": stock_user.money,
                "rank": stock_user.rank,
                "stocks": stock_user.stocks
            })

    @classmethod
    def get_stock(cls, stock: str):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["Stock"]
        return db.find_one({"stockName": stock})

    @classmethod
    def get_stocks(cls):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["Stock"]
        return db.find()

    @classmethod
    def create_stock(cls, post):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["Stock"]
        db.insert_one({
            "stockName": post["stockName"],
            "price": post["price"]
        })

    @classmethod
    def create_stock_user(cls, member: discord.Member):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["StockUser"]
        db.insert_one({
            "userId": member.id,
            "userName": member.name,
            "money": 0,
            "rank": 0,
            "stocks": {}
        })


class Title:
    def __init__(self) -> None:
        pass

    @classmethod
    async def add_title(cls, user: discord.Member, title):
        await user.add_roles(title)

    @classmethod
    async def remove_title(cls, user: discord.Member, title_):
        await user.remove_roles(title_)


@tree.command(guild=discord.Object(id=1038138701961769021), name="맞춤법", description="입력된 문장의 맞춤법을 검사합니다.")
async def grammer(interaction: discord.Interaction, msg: str):
    msg = ChatManager.checkGrammer(msg)
    if msg.original != msg.checked:
        await interaction.response.send_message(
            ephemeral=True,
            embed=discord.Embed(
                title='이렇게 바꾸는건 어떨까요 ?',
                description=f"{msg.original}\n  ➡{msg.checked}",
                color=COLOR
            )
        )
    else:
        await interaction.response.send_message(
            ephemeral=True,
            embed=discord.Embed(
                title='문법적 오류가 없습니다 !',
                color=COLOR
            )
        )


def get_timestamp(date: datetime):
    return f"{date.year}-{date.month}-{date.day} {date.hour}:{date.minute}:{date.second}"


@tree.command(guild=discord.Object(id=1038138701961769021), name="알람", description="알람을 설정합니다.")
async def remind(interaction: discord.Interaction, time: str, text: str):
    __time = Timer.calc(time)
    print(__time)
    timers.Timer(bot, "reminder", __time, args=(
        interaction.channel.id, interaction.user.id, text)).start()
    embed = discord.Embed(color=COLOR)
    __time += datetime.timedelta(hours=9)
    embed.add_field(
        name="✅ 알람설정 완료",
        value=f"설정된 시간: {get_timestamp(__time)}"
    )
    await interaction.response.send_message(embed=embed)


class MusicAddModal(discord.ui.Modal, title="노래 추가"):
    url = discord.ui.TextInput(label="url")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await bot.music.add(self.url.value)
        embed = discord.Embed(title="플레이리스트", description="곡이 추가 되었어요.", color=COLOR)
        for song in bot.music.playlist:
            embed.add_field(name=song["name"], value=song["url"], inline=False)
        await interaction.followup.send(embed=embed)


class MusicDelSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [discord.SelectOption(label=f"#{idx}. {song['name']}") for idx, song in enumerate(bot.music.playlist)]
        super().__init__(options=options)

    async def callback(self, interaction: discord.Interaction):
        for song in bot.music.playlist:
            if self.values[0][4:] == song["name"]:
                bot.music.playlist.remove(song)
                embed = discord.Embed(title="플레이리스트", description="노래가 삭제되었어요.", color=COLOR)
                for _song in bot.music.playlist:
                    embed.add_field(name=song["name"], value=_song["url"], inline=False)
                return await interaction.response.send_message(embed=embed)


class MusicDelView(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(MusicDelSelect())


@tree.command(guild=discord.Object(id=1038138701961769021), name="노래", description="노래관련 명령어를 실행합니다.")
@app_commands.describe(commands="명령어")
@app_commands.choices(commands=[
    app_commands.Choice(name="추가", value=1),
    app_commands.Choice(name="삭제", value=2),
    app_commands.Choice(name="재생", value=3),
    app_commands.Choice(name="일시정지", value=4),
    app_commands.Choice(name="스킵", value=5),
    app_commands.Choice(name="플레이리스트", value=6)
])
async def music(interaction: discord.Interaction, commands: app_commands.Choice[int]):
    match commands.name:
        case "추가":
            await interaction.response.send_modal(MusicAddModal())
        case "삭제":
            if bot.music.playlist:
                return await interaction.response.send_message(view=MusicDelView())
            embed = discord.Embed(title="플레이리스트", color=COLOR)
            embed.add_field(name="🚫 ERROR", value="플레이리스트에 노래가 없어요.")
            return await interaction.response.send_message(embed=embed)
        case "재생":
            await interaction.response.defer()
            await bot.music.connect(interaction.user.voice.channel)
            bot.music.play()
            embed = discord.Embed(title="재생", color=COLOR)
            await interaction.followup.send(embed=embed)
        case "일시정지":
            bot.music.pause()
            embed = discord.Embed(title="일시정지", color=COLOR)
            await interaction.response.send_message(embed=embed)
        case "스킵":
            bot.music.stop()
            embed = discord.Embed(title="플레이리스트", description="노래를 스킵합니다.", color=COLOR)
            for song in bot.music.playlist:
                embed.add_field(name=song["name"], value=song["url"], inline=False)
            await interaction.response.send_message(embed=embed)
        case "플레이리스트":
            embed = discord.Embed(title="플레이리스트", color=COLOR)
            for song in bot.music.playlist:
                embed.add_field(name=song["name"], value=song["url"], inline=False)
            await interaction.response.send_message(embed=embed)


class StockTradeModal(discord.ui.Modal):
    stock = discord.ui.TextInput(label="주식")
    cnt = discord.ui.TextInput(label="갯수")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        pass


class StockBuyModal(StockTradeModal, title="주식 구매"):
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        user = StockUser(interaction.user.name)
        stock_ = Stock(self.stock.value)
        StockGame.buy(user, stock_, int(self.cnt.value))
        embed = discord.Embed(title="구매 완료", color=COLOR)
        embed.add_field(name="구입한 주식", value=self.stock.value)
        embed.add_field(name="구입한 갯수", value=self.cnt.value)
        await interaction.followup.send(embed=embed)


class StockSellModal(StockTradeModal, title="주식 판매"):
    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        user = StockUser(interaction.user.name)
        stock_ = Stock(self.stock.value)
        StockGame.sell(user, stock_, int(self.cnt.value))
        embed = discord.Embed(title="판매 완료", color=COLOR)
        embed.add_field(name="판매한 주식", value=self.stock.value)
        embed.add_field(name="판매한 갯수", value=self.cnt.value)
        await interaction.followup.send(embed=embed)


@tree.command(guild=discord.Object(id=1038138701961769021), name="주식", description="주식관련 명령어를 실행합니다.")
@app_commands.describe(commands="명령어")
@app_commands.choices(commands=[
    app_commands.Choice(name="구매", value=1),
    app_commands.Choice(name="판매", value=2),
    app_commands.Choice(name="현황", value=3),
    app_commands.Choice(name="지갑", value=4)
])
async def stock(interaction: discord.Interaction, commands: app_commands.Choice[int]):
    match commands.name:
        case "구매":
            await interaction.response.send_modal(StockBuyModal())
        case "판매":
            await interaction.response.send_modal(StockSellModal())
        case "현황":
            stocks = DB.get_stocks()
            embed = discord.Embed(title="주식 현황")
            for stock in stocks:
                embed.add_field(name=stock["stockName"], value=stock["price"])
            await interaction.response.send_message(embed=embed)
        case "지갑":
            user = StockUser(interaction.user.name)
            embed = discord.Embed(title=f"{interaction.user.name}님의 지갑", color=COLOR)
            embed.add_field(name="money", value=user.money, inline=False)
            for key, value in user.stocks.items():
                embed.add_field(name=key, value=value, inline=False)
            await interaction.response.send_message(embed=embed)


class RoomCreateModal(discord.ui.Modal, title="방 생성"):
    name = discord.ui.TextInput(label="방 이름")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        isroom = False
        for room in rooms:
            if room.name == self.name.value:
                # checkroom
                isroom = True
        if not isroom and endtalk.get_room(interaction.user) is None:
            temp = Room(self.name.value)
            temp.user_list.append(interaction.user)
            rooms.append(temp)
            await interaction.response.send_message(
                embed=discord.Embed(title='끝말잇기 방 생성 완료', description=f"{interaction.user}님", color=COLOR))
        else:
            await interaction.response.send_message(
                embed=discord.Embed(title='끝말잇기 방이 이미 존재하거나 이미 참여했어요.', description=f"{interaction.user}님", color=COLOR))


class RoomJoinSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [discord.SelectOption(label=f"#{idx}. {room.name}") for idx, room in enumerate(rooms)]
        super().__init__(options=options)

    async def callback(self, interaction: discord.Interaction):
        room = endtalk.get_room(interaction.user)
        if room:
            embed = discord.Embed(title="끝말잇기", color=COLOR)
            embed.add_field(name="🚫 ERROR", value=f"이미 {room.name}에 참가중 이에요.")
            return await interaction.response.send_message(embed=embed)

        for room in rooms:
            if room.name == self.values[0][4:]:
                roomnumber = rooms.index(room) - 1
                temp = rooms.pop(roomnumber)
                temp.user_list.append(interaction.user)
                rooms.append(temp)
                return await interaction.response.send_message(
                    embed=discord.Embed(title='끝말잇기 참가 완료', description=f"{interaction.user}님", color=COLOR))


class RoomJoinView(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(RoomJoinSelect())


@tree.command(guild=discord.Object(id=1038138701961769021), name="끝말잇기", description="끝말잇기관련 명령어를 실행합니다.")
@app_commands.describe(commands="명령어")
@app_commands.choices(commands=[
    app_commands.Choice(name="방 생성", value=1),
    app_commands.Choice(name="방 참가", value=2),
    app_commands.Choice(name="방 목록", value=3),
    app_commands.Choice(name="시작", value=4),
    app_commands.Choice(name="종료", value=5)
])
async def end_game(interaction: discord.Interaction, commands: app_commands.Choice[int]):
    match commands.name:
        case "방 생성":
            print(rooms)
            await interaction.response.send_modal(RoomCreateModal())
        case "방 참가":
            await interaction.response.send_message(view=RoomJoinView())
        case "방 목록":
            roomnamelist = []
            for room in rooms:
                roomnamelist.append(room.name)
                roomnamelist.append(room.user_list)
            await interaction.response.send_message(
                embed=discord.Embed(title="방 목록입니다.", description=f"{roomnamelist}", color=COLOR))
        case "시작":
            room = endtalk.get_room(interaction.user)
            if room:
                room.is_playing = True
                room.last_user = room.user_list[0]
                return await interaction.response.send_message(
                    embed=discord.Embed(title="끝말잇기 시작", description=f"{room.user_list[0]}님부터 시작해 주세요",
                                        color=COLOR))
            await interaction.response.send_message(
                embed=discord.Embed(title="시작하지 못해요 ...", description="참가 먼저 해주세요", color=COLOR))
        case "종료":
            room = endtalk.get_room(interaction.user)
            if room:
                room.is_playing = False
                rooms.remove(room)
                return await interaction.response.send_message(embed=discord.Embed(title="끝말잇기 종료", color=COLOR))
            await interaction.response.send_message(
                embed=discord.Embed(title="종료하지 못해요 ...", description="종료할 방이 없거나 시작 먼저 해주세요", color=COLOR))


@tree.command(guild=discord.Object(id=1038138701961769021), name="칭호", description="칭호를 추가하거나 제거합니다.")
async def title(interaction: discord.Interaction, username: str, title_name: str):
    role = discord.utils.find(
        lambda r: r.name == title_name, interaction.guild.roles)

    user = discord.utils.find(
        lambda m: m.name == username, interaction.guild.members)

    embed = discord.Embed(color=COLOR)
    # 칭호가 존재하지 않을 경우
    if role is None:
        embed.add_field(name="🚫 ERROR", value=f"그런 칭호는 존재하지 않아요.")
        embed.set_footer(text=f"입력한 칭호: {title_name}")
        await interaction.response.send_message(embed=embed)
        return

    # 유저가 존재하지 않을 경우
    if user is None:
        embed.add_field(name="🚫 ERROR", value=f"그런 사람은 존재하지 않아요. {username}")
        embed.set_footer(text=f"입력한 유저: {username}")
        await interaction.response.send_message(embed=embed)
        return

    # 칭호 제거
    if role in user.roles:
        await Title.remove_title(user, role)
        embed.add_field(name="✅ SUCCESS", value="칭호를 제거했어요.")
        embed.set_footer(text=f"제거된 유저: {username}, 제거한 칭호: {title_name}")
        await interaction.response.send_message(embed=embed)
    # 칭호 추가
    else:
        await Title.add_title(user, role)
        embed.add_field(name="✅ SUCCESS", value="칭호를 추가했어요.")
        embed.set_footer(text=f"입력한 유저이름: {username}")
        embed.set_footer(text=f"추가된 유저: {username}, 추가한 칭호: {title_name}")
        await interaction.response.send_message(embed=embed)


@tree.command(guild=discord.Object(id=1038138701961769021), name="경험치", description="유저의 경험치 상태와 랭킹을 확인합니다.")
async def status(interaction: discord.Interaction, username: str):
    embed = discord.Embed(title="경험치", color=COLOR)
    # 유저가 없는 경우
    if not discord.utils.find(lambda m: m.name == username, interaction.guild.members):
        embed.add_field(name="🚫 ERROR", value="그런 사람은 존재하지 않아요.")
    else:
        DB.refresh_exp_ranking()
        user = Status(username)
        embed.add_field(name="name", value=user.userName, inline=False)
        embed.add_field(name="exp", value=user.exp, inline=False)
        embed.add_field(name="rank", value=f"{user.rank}등", inline=False)
    await interaction.response.send_message(embed=embed)


# @ tree.command(guild=discord.Object(id=1038138701961769021), name="유저등록", description="status 유저를 등록합니다.")
# async def status_create_user(interaction: discord.Interaction):
#     DB.createStatusUser(interaction)
#     await interaction.response.send_message("생성되었습니다.")


# @tree.command(guild=discord.Object(id=1038138701961769021), name="주식생성", description="주식생성")
# async def stock_create(interaction: discord.Interaction, stockname: str, price: int):
#     DB.create_stock({
#         "stockName": stockname,
#         "price": price
#     })
#     await interaction.response.send_message("생성되었습니다.")


# @ tree.command(guild=discord.Object(id=1038138701961769021), name="주식유저생성", description="주식유저생성")
# async def stock_user_create(interaction: discord.Interaction, username: str):
#     member: discord.Member = discord.utils.find(
#         lambda m: m.name == username, interaction.guild.members)
#     DB.create_stock_user(member=member)
#     await interaction.response.send_message("생성 완료")

bot.run(os.environ["BOT"])
