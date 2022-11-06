import discord
from pymongo import MongoClient
from discord import app_commands
import youtube_dl
from collections import deque


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


class Music():
    def __init__(self) -> None:
        self.__vc = None
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
            url = info['formats'][0]['url']
            self.playlist.append(
                await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS))

    async def connect(self):
        voiceChannel = bot.get_channel(1038138702670614551)
        if self.__vc is None:
            self.__vc: discord.VoiceClient = await voiceChannel.connect()

    def play(self):
        if self.__vc.is_paused():
            self.__vc.resume()
        elif self.playlist:
            self.__vc.play(self.playlist[0],
                           after=lambda e: self.play())
            self.playlist.popleft()

    def pause(self):
        self.__vc.pause()

    def stop(self):
        self.__vc.stop()


class Status():
    def __init__(self) -> None:
        pass

    @classmethod
    def getStatus(self, username: str) -> dict:
        client = MongoClient(
            "URL")

        db = client["Discord"]["User"]
        # TODO 아무도 찾지 못했을 경우 예외처리가 필요
        user = db.find_one({"userName": username})
        return user

    @classmethod
    def createStatus(self, post: dict):
        client = MongoClient(
            "URL")

        db = client["Discord"]["User"]
        # TODO 저장이 되었는지 확인하는 코드가 필요
        db.insert_one(post)
        return True

    @classmethod
    def refreshRanking(self):
        client = MongoClient(
            "URL")

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


class Title():
    def __init__(self) -> None:
        pass

    @classmethod
    async def addTitle(self, user: discord.Member, title):
        await user.add_roles(title)

    @classmethod
    async def removeTitle(self, user: discord.Member, title):
        await user.remove_roles(title)


bot = Bot()
tree = app_commands.CommandTree(bot)


@tree.command(guild=discord.Object(id=1038138701961769021), name="test", description="testing")
async def _self(interaction: discord.Interaction):
    await interaction.response.send_message("complete")


@tree.command(guild=discord.Object(id=1038138701961769021), name="생성", description="끝말잇기를 진행할 방을 생성합니다")
async def _create(interaction: discord.Interaction, name: str):
    await interaction.response.send_message(f"I am working! {name}", ephemeral=True)


@tree.command(guild=discord.Object(id=1038138701961769021), name="곡추가", description="노래를 추가합니다.")
async def __add(interaction: discord.Interaction, url: str):
    await bot.music.add(url)
    await interaction.response.send_message("추가 되었습니다.")


@tree.command(guild=discord.Object(id=1038138701961769021), name="재생", description="노래를 재생합니다.")
async def _music(interaction: discord.Interaction):
    await interaction.response.defer()
    await bot.music.connect()
    bot.music.play()
    await interaction.followup.send("재생")


# FIXME 정상작동 X
@tree.command(guild=discord.Object(id=1038138701961769021), name="곡삭제", description="노래를 삭제합니다.")
async def _remove(interaction: discord.Interaction, num: str):
    bot.music.playlist.remove(bot.music.playlist[int(num)])
    await interaction.response.send_message("삭제 되었습니다.")


# FIXME 정상작동 X
@tree.command(guild=discord.Object(id=1038138701961769021), name="플레이리스트", description="플레이리스트를 보여줍니다.")
async def _playlist(interaction: discord.Interaction):
    await interaction.response.send_message(bot.music.playlist)


@tree.command(guild=discord.Object(id=1038138701961769021), name="일시정지", description="노래를 일시정지합니다.")
async def _pause(interaction: discord.Interaction):
    bot.music.pause()
    await interaction.response.send_message("일시정지")


@tree.command(guild=discord.Object(id=1038138701961769021), name="스킵", description="노래를 스킵합니다.")
async def _stop(interaction: discord.Interaction):
    bot.music.stop()
    await interaction.response.send_message("스킵")

# 매개변수를 lowercase로 작성하지 않으면 error 발생


@tree.command(guild=discord.Object(id=1038138701961769021), name="칭호", description="칭호를 추가하거나 제거합니다")
async def _title(interaction: discord.Interaction, username: str, title_name: str):
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


@tree.command(guild=discord.Object(id=1038138701961769021), name="경험치", description="유저의 경험치 상태와 랭킹을 확인합니다")
async def _level(interaction: discord.Interaction, username: str):
    if not discord.utils.find(lambda m: m.name == username, interaction.guild.members):
        return
    Status.refreshRanking()
    user = Status.getStatus(username)

    # TODO 예쁘게 꾸며서 메세지 보내도록 해야함
    await interaction.response.send_message(user)


bot.run("TOKEN")