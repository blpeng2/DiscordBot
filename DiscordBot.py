import discord
from pymongo import MongoClient
from discord import app_commands
import youtube_dl
from collections import deque, defaultdict
import requests
import os
from dotenv import load_dotenv
import hgtk
import datetime
from discord.ext import timers
from hanspell import spell_checker

load_dotenv()
apikey = os.getenv('APIKEY')
blacklist = ['즘', '틱', '늄', '슘', '퓸', '늬', '뺌', '섯', '숍', '튼', '름', '늠', '쁨']


class Timer():
    @classmethod
    def calc(self, time):
        if time[-1] == "뒤":
            time = time[:-1].strip()
            arrayOfTime = time.split()
            date = datetime.datetime.now()
            for __time in arrayOfTime:
                if __time[-1] == "초":
                    date += datetime.timedelta(seconds=int(__time[:-1]))
                elif __time[-1] == "분":
                    date += datetime.timedelta(minutes=int(__time[:-1]))
                elif __time[-2:] == "시간":
                    date += datetime.timedelta(hours=int(__time[:-2]))
        else:
            pass
        date -= datetime.timedelta(hours=9)
        return date


class Music():
    def __init__(self) -> None:
        self.__voiceClient = None
        self.playlist = deque()
        self.is_playing = False

    async def add(self, url):
        YDL_OPTIONS = {
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
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['formats'][0]['url']
            self.playlist.append(
                {
                    "audio": await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS),
                    "name": info["title"],
                    "url": url
                })

    async def connect(self, voiceChannel):
        if self.__voiceClient is None:
            self.__voiceClient: discord.VoiceClient = await voiceChannel.connect()

    def play(self):
        if self.__voiceClient.is_paused():
            self.__voiceClient.resume()
        elif self.playlist:
            self.__voiceClient.play(self.playlist[0]["audio"], after=self.play)
            self.playlist.popleft()

    def pause(self):
        self.__voiceClient.pause()

    def stop(self):
        self.__voiceClient.stop()


class Stock():
    def __init__(self, stockName) -> None:
        stock = DB.getStock(stockName)
        self.stockName = stock["stockName"]
        self.price = stock["price"]

    def getStock(self):
        return {
            "stockName": self.stockName,
            "price": self.price
        }


class StockUser():
    def __init__(self, userName) -> None:
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["StockUser"]
        stockUser = db.find_one({"userName": userName})
        self.userId = stockUser["userId"]
        self.userName = stockUser["userName"]
        self.money = stockUser["money"]
        self.rank = stockUser["rank"]
        self.stocks = defaultdict(int, stockUser["stocks"])


class StockGame():
    @classmethod
    def buy(self, user: StockUser, stock: Stock):
        stockUser = StockUser(user.userName)
        stockUser.money -= stock.price
        stockUser.stocks[stock.stockName] += 1
        DB.updateStockUser(stockUser)

    @classmethod
    def sell(self, user: StockUser, stock: Stock):
        stockUser = StockUser(user.userName)
        stockUser.money += stock.price
        stockUser.stocks[stock.stockName] -= 1
        DB.updateStockUser(stockUser)


class Room():
    def __init__(self, name) -> None:
        self.name = name
        self.is_playing = False
        self.user_list = []
        self.last_word = ""
        self.history = []
        self.last_user = name

    def __call__(self):
        return self.user_list


rooms = []


class EndTalk():

    # string list에서 단어, 품사와 같은 요소들을 추출할때 사용됩니다
    def midReturn(val, s, e):
        if s in val:
            val = val[val.find(s)+len(s):]
            if e in val:
                val = val[:val.find(e)]
        return val
    # string에서 XML 등의 요소를 분석할때 사용됩니다

    def midReturn_all(val, s, e):
        if s in val:
            tmp = val.split(s)
            val = []
            for i in range(0, len(tmp)):
                if e in tmp[i]:
                    val.append(tmp[i][:tmp[i].find(e)])
        else:
            val = []
        return val

    def checkword(self, query, room):
        room.last_word = endtalk.convert(query[0])
        url = 'https://krdict.korean.go.kr/api/search?key=' + apikey + '&part=word&sort=popular&num=100&pos=1&q=' + query
        response = requests.get(url, verify=False)
        ans = ''
        words = EndTalk.midReturn_all(response.text, '<item>', '</item>')
        for w in words:
            if not (w in room.history):
                word = EndTalk.midReturn(w, '<word>', '</word>')
                pos = EndTalk.midReturn(w, '<pos>', '</pos>')
                if len(word) > 1 and pos == '명사' and word == query:
                    ans = w
        if len(ans) > 0:
            return EndTalk.midReturn(ans, '<word>', '</word>')
        else:
            return ''
    def convert(self, rear):
        convertList = {"라":"나","락":"낙","란":"난","랄":"날",
        "람":"남","랍":"납","랏":"낫","랑":"낭",
        "략":"약","량":"양","렁":"넝","려":"여",
        "녀":"여","력":"역","녁":"역","련":"연",
        "년":"연","렬":"열","렴":"염","념":"염",
        "렵":"엽","령":"영","녕":"영","로":"노",
        "록":"녹","론":"논","롤":"놀","롬":"놈",
        "롭":"놉","롯":"놋","롱":"농","료":"요",
        "뇨":"요","룡":"용","뇽":"용","루":"누",
        "룩":"눅","룬":"눈","룰":"눌","룸":"눔",
        "룻":"눗","룽":"눙","류":"유","뉴":"유",
        "륙":"육","률":"율","르":"느","륵":"늑",
        "른":"는","를":"늘","름":"늠","릅":"늡",
        "릇":"늣","릉":"능","래":"내","랙":"낵",
        "랜":"낸","랠":"낼","램":"냄","랩":"냅",
        "랫":"냇","랭":"냉","례":"예","뢰":"뇌",
        "리":"이","니":"이","린":"인","닌":"인",
        "릴":"일","닐":"일","림":"임","님":"임",
        "립":"입","닙":"입","릿":"잇","닛":"잇",
        "링":"잉","닝":"잉"}

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

    async def on_message(self, msg: discord.Message):
        if msg.author == bot.user:
            return
        if ChatManager.checkAbuse(msg.content):
            await msg.channel.purge(limit=1)
            embed = discord.Embed(title="욕설 금지")
            embed.add_field(name=f"{msg.author}님", value="욕설을 사용하시면 안되죠")
            await msg.channel.send(embed=embed)
            return
        for room in rooms:
            if room.is_playing and (msg.author == room.last_user):
                result = endtalk.checkword(msg.content, room)
                if len(result) == 1:
                    await msg.channel.send("적어도 두 글자가 되어야 합니다")
                elif result == '':
                    await msg.channel.send("없는 단어입니다.")
                elif result in room.history:
                    await msg.channel.send("이미 사용한 단어입니다.")
                elif result[len(result)-1] in blacklist:
                    await msg.channel.send("아.. 좀 치사한데요..")
                elif room.last_word != result[0] and room.last_word != "":
                    await msg.channel.send(f"{room.last_word}(으)로 시작하는 단어를 입력해 주십시오.")
                else:
                    if room.user_list.index(room.last_user) - 1 == len(room.user_list):
                        room.last_user = room.user_list[0]
                    else:
                        room.last_user = room.user_list[room.user_list.index(
                            room.last_user)]
                    room.history.append(msg.content)
                    room.last_word = result[-1]
                    print(room.last_word)
                    await msg.channel.send(f"{result} > 단어 받았습니다. {room.last_word}(으)로 시작하는 단어 {room.last_user}님 차례!")
        # DB에 유저가 없으면 user.userName = None 
        user = Status(msg.author.name)
        if user.userName: user.addExp(10)

    async def on_reminder(self, channel_id, author_id, text):
        channel = bot.get_channel(channel_id)
        await channel.send("<@{0}>님, 알람입니다: {1}".format(author_id, text))


bot = Bot()
tree = app_commands.CommandTree(bot)


class ChatManager():
    @classmethod
    def checkGrammer(self, msg):
        return spell_checker.check(msg)

    @ classmethod
    def checkAbuse(self, msg: str):
        API_URL = os.getenv("NLP")
        headers = {
            "Authorization": os.getenv("MACHINE")}
        payload = {
            "inputs": f"{msg}",
            "options": {
                "wait_for_model": True
            }
        }
        response = requests.post(API_URL, headers=headers, json=payload).json()
        if response[0][0]["label"] == "hate":
            return True
        return False


class Status():
    def __init__(self, userName) -> None:
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["User"]
        user = db.find_one({"userName": userName})
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

    def getStatus(self):
        return {
            "userId": self.userId,
            "userName": self.userName,
            "exp": self.exp,
            "level": self.level,
            "rank": self.rank
        }

    def addExp(self, exp):
        self.exp += exp
        DB.updateUser(self.getStatus())

    def getUser(self):
        return DB.getUser(self.userName)


class DB():
    @classmethod
    def getUser(self, userName) -> dict | None:
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["User"]
        return db.find_one({"userName": userName})

    @classmethod
    def updateUser(self, status):
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
    def createStatusUser(self, interaction: discord.Interaction):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["User"]
        db.insert_one({
            "userId": interaction.user.id,
            "userName": interaction.user.name,
            "exp": 0,
            "level": 0,
            "rank": 0
        })

    @ classmethod
    def refreshExpRanking(self):
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
    def refreshStockUserRanking(self):
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
    def updateStockUser(self, stockUser: StockUser):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["StockUser"]
        db.replace_one(
            {
                "userName": stockUser.userName},
            {
                "userId": stockUser.userId,
                "userName": stockUser.userName,
                "money": stockUser.money,
                "rank": stockUser.rank,
                "stocks": stockUser.stocks
            })

    @classmethod
    def getStock(self, stock: str):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["Stock"]
        return db.find_one({"stockName": stock})

    @classmethod
    def getStocks(self):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["Stock"]
        return db.find()

    @classmethod
    def createStock(self, post):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["Stock"]
        db.insert_one({
            "stockName": post["stockName"],
            "price": post["price"]
        })

    @classmethod
    def createStockUser(self, post):
        client = MongoClient(os.getenv("MONGO"))
        db = client["Discord"]["StockUser"]
        db.insert_one({
            "userId": post["userId"],
            "userName": post["userName"],
            "money": post["money"],
            "rank": post["rank"],
            "stocks": post["stocks"]
        })


class Title():
    def __init__(self) -> None:
        pass

    @ classmethod
    async def addTitle(self, user: discord.Member, title):
        await user.add_roles(title)

    @ classmethod
    async def removeTitle(self, user: discord.Member, title):
        await user.remove_roles(title)


@tree.command(guild=discord.Object(id=1038138701961769021), name="끝말잇기생성", description="끝말잇기방을 생성합니다.")
async def _create(interaction: discord.Interaction, roomname: str):
    isroom = False
    for room in rooms:
        if room.name == roomname:
            # checkroom
            isroom = True
    if not isroom:
        temp = Room(roomname)
        temp.user_list.append(interaction.user)
        rooms.append(temp)
        await interaction.response.send_message(embed=discord.Embed(title='끝말잇기 방 생성 완료', description=f"{interaction.user}님", color=0xeeafaf))
    else:
        await interaction.response.send_message(embed=discord.Embed(title='끝말잇기 방이 이미 있습니다.', description=f"{interaction.user}님", color=0xeeafaf))


@tree.command(guild=discord.Object(id=1038138701961769021), name="끝말잇기참가", description="끝말잇기방에 참가합니다.")
async def _join(interaction: discord.Interaction, roomname: str):
    isroom = False
    roomnumber = 0
    for room in rooms:
        if room.name == roomname:
            isroom == True
            roomnumber = rooms.index(room)
    if isroom:
        temp = rooms.pop(roomnumber)
        temp.user_list.append(interaction.user)
        rooms.append(temp)
        await interaction.response.send_message(embed=discord.Embed(title='끝말잇기 참가 완료', description=f"{interaction.user}님", color=0xeeafaf))
    else:
        await interaction.response.send_message(embed=discord.Embed(title='이미 참가했거나 찾는 끝말잇기 방이 없습니다', description=f"{interaction.user}님", color=0xeeafaf))


@tree.command(guild=discord.Object(id=1038138701961769021), name="끝말잇기시작", description="입력된 방의 끝말잇기게임를 시작합니다.")
async def _start(interaction: discord.Interaction, roomname: str):
    isroom = False
    for room in rooms:
        if room.name == roomname:
            isroom == True
            room.is_playing = True
            room.last_user = room.user_list[0]
            await interaction.response.send_message(embed=discord.Embed(title="끝말잇기 시작", description=f"{room.user_list[0]}님부터 시작해 주세요", color=0xeeafaf))
            return
        await interaction.response.send_message(embed=discord.Embed(title="시작하지 못해요 ...", description="참가 먼저 해주세요", color=0xeeafaf))


@tree.command(guild=discord.Object(id=1038138701961769021), name="끝말잇기종료", description="입력된 방의 끝말잇기게임를 종료합니다.")
async def _end(interaction: discord.Interaction, roomname: str):
    isroom = False
    for room in rooms:
        if room.name == roomname:
            isroom == True
            room.is_playing = False
            await interaction.response.send_message(embed=discord.Embed(title="끝말잇기 종료", color=0xeeafaf))
            return
        await interaction.response.send_message(embed=discord.Embed(title="종료하지 못해요 ...", description="종료할 방이 없거나 시작 먼저 해주세요", color=0xeeafaf))


@tree.command(guild=discord.Object(id=1038138701961769021), name="끝말잇기방", description="생성된 끝말잇기방을 확인합니다.")
async def _room_list(interaction: discord.Interaction):
    roomnamelist = []
    for room in rooms:
        roomnamelist.append(room.name)
    await interaction.response.send_message(embed=discord.Embed(title="방 목록입니다.", description=f"{roomnamelist}", color=0xeeafaf))


@ tree.command(guild=discord.Object(id=1038138701961769021), name="맞춤법", description="입력된 문장의 맞춤법을 검사합니다.")
async def grammer(interaction: discord.Interaction, msg: str):
    msg = ChatManager.checkGrammer(msg)
    if msg.original != msg.checked:
        await interaction.response.send_message(ephemeral=True, embed=discord.Embed(title='이렇게 바꾸는건 어떨까요 ?', description=f"{msg.original}\n  ➡{msg.checked}", color=0x00ff00))
    else:
        await interaction.response.send_message(ephemeral=True, embed=discord.Embed(title='문법적 오류가 없습니다 !', color=0x00ff00))


@ tree.command(guild=discord.Object(id=1038138701961769021), name="알람", description="알람을 설정합니다.")
async def remind(interaction: discord.Interaction, time: str, text: str):
    timers.Timer(bot, "reminder", Timer.calc(time), args=(
        interaction.channel.id, interaction.user.id, text)).start()
    await interaction.response.send_message("알람설정 완료")

class MusicAddModal(discord.ui.Modal, title="노래 추가"):
    url = discord.ui.TextInput(label="url")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await bot.music.add(self.url.value)
        embed = discord.Embed(title="플레이리스트", description="곡이 추가 되었습니다.")
        for song in bot.music.playlist:
            embed.add_field(name=song["name"], value=song["url"], inline=False)
        await interaction.response.send_message(embed=embed)

class MusicDelModal(discord.ui.Modal, title="노래 삭제"):
    num = discord.ui.TextInput(label="num")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        bot.music.playlist.remove(bot.music.playlist[int(self.num.value) + 1])
        embed = discord.Embed(title="플레이리스트", description="곡이 삭제 되었습니다.")
        for song in bot.music.playlist:
            embed.add_field(name=song["name"], value=song["url"], inline=False)
        await interaction.response.send_message(embed=embed)

@ tree.command(guild=discord.Object(id=1038138701961769021), name="노래", description="노래관련 명령어를 실행합니다.")
@ app_commands.describe(commands="명령어")
@ app_commands.choices(commands=[
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
            await interaction.response.send_modal(MusicDelModal())
        case "재생":
            await interaction.response.defer()
            await bot.music.connect(interaction.user.voice.channel)
            bot.music.play()
            await interaction.followup.send("재생")
        case "일시정지":
            bot.music.pause()
            await interaction.response.send_message("일시정지")
        case "스킵":
            bot.music.stop()
            embed = discord.Embed(title="플레이리스트", description="노래를 스킵합니다.")
            for song in bot.music.playlist:
                embed.add_field(name=song["name"], value=song["url"], inline=False)
            await interaction.response.send_message(embed=embed)
        case "플레이리스트":
            embed = discord.Embed(title="플레이리스트")
            for song in bot.music.playlist:
                embed.add_field(name=song["name"], value=song["url"], inline=False)
            await interaction.response.send_message(embed=embed)

@ tree.command(guild=discord.Object(id=1038138701961769021), name="칭호", description="칭호를 추가하거나 제거합니다.")
async def title(interaction: discord.Interaction, username: str, title_name: str):
    role = discord.utils.find(
        lambda r: r.name == title_name, interaction.guild.roles)

    user = discord.utils.find(
        lambda m: m.name == username, interaction.guild.members)

    # 칭호가 존재하지 않을 경우 예외처리
    if role is None:
        await interaction.response.send_message("칭호가 존재하지 않습니다", ephemeral=True)
        return

    if user is None:
        await interaction.response.send_message("유저가 존재하지 않습니다.", ephemeral=True)

    if role in user.roles:
        await Title.removeTitle(user, role)
        await interaction.response.send_message("칭호를 제거했습니다.", ephemeral=True)
    else:
        await Title.addTitle(user, role)
        await interaction.response.send_message("칭호를 추가했습니다.", ephemeral=True)


@ tree.command(guild=discord.Object(id=1038138701961769021), name="경험치", description="유저의 경험치 상태와 랭킹을 확인합니다.")
async def status(interaction: discord.Interaction, username: str):
    embed = discord.Embed(title="경험치")
    # 유저가 없는 경우
    if not discord.utils.find(lambda m: m.name == username, interaction.guild.members):
        embed.add_field(name="🚫ERROR🚫", value="그런 사람은 존재하지 않아요.")
    else:
        DB.refreshExpRanking()
        user = Status(username)
        embed.add_field(name="name", value=user.userName, inline=False)
        embed.add_field(name="exp", value=user.exp, inline=False)
        embed.add_field(name="rank", value=f"{user.rank}등", inline=False)
    await interaction.response.send_message(embed=embed)

@ tree.command(guild=discord.Object(id=1038138701961769021), name="유저등록", description="status 유저를 등록합니다.")
async def status_create_user(interaction: discord.Interaction):
    DB.createStatusUser(interaction)
    await interaction.response.send_message("생성되었습니다.")

@ tree.command(guild=discord.Object(id=1038138701961769021), name="구매", description="구매")
async def stock_buy(interaction: discord.Interaction, stockname: str):
    user = StockUser(interaction.user.name)
    stock = Stock(stockname)
    StockGame.buy(user, stock)
    await interaction.response.send_message("구매했습니다.")


@ tree.command(guild=discord.Object(id=1038138701961769021), name="판매", description="판매")
async def stock_sell(interaction: discord.Interaction, stockname: str):
    user = StockUser(interaction.user.name)
    stock = Stock(stockname)
    StockGame.sell(user, stock)
    await interaction.response.send_message("판매했습니다.")


@ tree.command(guild=discord.Object(id=1038138701961769021), name="지갑", description="지갑")
async def stock_wallet(interaction: discord.Interaction):
    user = StockUser(interaction.user.name)
    await interaction.response.send_message(user.money)


@ tree.command(guild=discord.Object(id=1038138701961769021), name="주식현황", description="주식현황")
async def stock_stocks(interaction: discord.Interaction):
    stocks = DB.getStocks()
    arr = []
    for stock in stocks:
        arr.append({
            "name": stock["stockName"],
            "price": stock["price"]
        })
    await interaction.response.send_message(arr)


@ tree.command(guild=discord.Object(id=1038138701961769021), name="주식생성", description="주식생성")
async def stock_create(interaction: discord.Interaction, stockname: str, price: int):
    DB.createStock({
        "stockName": stockname,
        "price": price
    })
    await interaction.response.send_message("생성되었습니다.")


@ tree.command(guild=discord.Object(id=1038138701961769021), name="주식유저생성", description="주식유저생성")
async def stock_user_create(interaction: discord.Interaction, username: str):
    user = discord.utils.find(
        lambda m: m.name == username, interaction.guild.members)
    DB.createStockUser({
        "userId": user.id,
        "userName": username,
        "money": 0,
        "rank": 0,
        "stocks": {}
    })
    await interaction.response.send_message("생성 완료")

bot.run(os.environ["BOT"])
