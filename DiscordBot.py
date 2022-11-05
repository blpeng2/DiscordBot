import discord
from pymongo import MongoClient
from discord import app_commands


class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.synced = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await tree.sync(guild=discord.Object(id=1038138701961769021))
            self.synced = True
        print(f"we have logged in as {self.user}.")


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
    Status.refreshRanking()
    await interaction.response.send_message("complete")


@tree.command(guild=discord.Object(id=1038138701961769021), name="생성", description="끝말잇기를 진행할 방을 생성합니다")
async def _create(interaction: discord.Interaction, name: str):
    await interaction.response.send_message(f"I am working! {name}", ephemeral=True)


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
