import shutil, random, time
from typing import List, Tuple
from pathlib import Path
import ujson as json
from httpx import AsyncClient
from nonebot import require, logger, on_command
from nonebot.plugin import PluginMetadata
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, ArgPlainText
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageSegment,
    MessageEvent,
    ActionFailed
)

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store


usage: str = """

随机wife
随机老婆
抽wife
抽老婆

添加wife [名字] [图片]
删除wife [名字]
查找wife [名字]

清空wife库
重置wife库

""".strip()


__plugin_meta__ = PluginMetadata(
    name="每日wife",
    description="每日随机二次元老婆",
    usage=usage,
    type="application",
    homepage="https://github.com/tkgs0/nonebot-plugin-wife",
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "月ヶ瀬"
    }
)


initial: Path = Path(__file__).parent / "resource"

datapath: Path = store.get_plugin_data_dir() / "random_wife"
datapath.mkdir(parents=True, exist_ok=True)

wifedir: Path =  datapath / "resource"
if not wifedir.is_dir():
    shutil.copytree(initial, wifedir)

wifelist: list[Path] = [ i for i in wifedir.rglob(r'*') ]

filepath: Path = datapath / "registers.json"

registers: dict = (
    json.loads(filepath.read_text("utf-8"))
    if filepath.is_file()
    else {"registers": {}}
)


def save_file() -> None:
    filepath.write_text(
        json.dumps(registers, indent=2, ensure_ascii=False), "utf-8")


def err_info(e: ActionFailed) -> str:
    e1 = 'Failed: '
    if e2 := e.info.get('wording'):
        return e1 + e2
    elif e2 := e.info.get('msg'):
        return e1 + e2
    else:
        return repr(e)


randwife = on_command(
    "抽wife",
    aliases={"抽老婆", "随机wife", "随机老婆", "今日wife", "今日老婆"},
    priority=15,
    block=True
)


@randwife.handle()
async def _(event: MessageEvent):
    _time = int(time.strftime("%Y%m%d", time.localtime()))
    uid = str(event.user_id)
    user = registers["registers"].get(uid)
    if user and _time == user[0]:
        img = wifedir / user[1]
    else:
        img = get_wife(uid, _time)

    while img and not img.is_file():
        clean_list(img)
        img = get_wife(uid, _time)

    try:
        await randwife.finish(Message(f"{event.sender.card or event.sender.nickname or uid}今天的wife是\n{img.name}\n{MessageSegment.image(img.read_bytes())}\n哦~" if img else "没有找到wife (悲"))
    except ActionFailed as e:
        logger.error(repr(e))
        await randwife.finish(err_info(e))


def clean_list(img: Path) -> None:
    try:
        wifelist.remove(img)
    except ValueError:
        pass


def get_wife(uid: str, _time: int) -> Path | None:
    if not wifelist:
        return None
    img = random.choice(wifelist)
    registers["registers"][uid] = [_time, img.name]
    save_file()
    return img


search_wife = on_command(
    "查找wife",
    permission=SUPERUSER,
    priority=5,
    block=True
)

@search_wife.handle()
async def _(
    matcher: Matcher,
    args: Message = CommandArg()
):
    msg: str = args.extract_plain_text()
    if msg:
        matcher.set_arg('ARGS', args)

@search_wife.got("ARGS", prompt="需要wife名")
async def _(args: str = ArgPlainText('ARGS')):
    if not (name := args.strip()):
        await search_wife.reject()
    _file = wifedir / name
    try:
        await search_wife.finish(Message(f"{name}\n{MessageSegment.image(_file.read_bytes())}" if _file.is_file() else "没有找到这个wife (悲"))
    except ActionFailed as e:
        logger.error(repr(e))
        await randwife.finish(err_info(e))


del_all_wife = on_command(
    "清空wife库",
    permission=SUPERUSER,
    priority=5,
    block=True
)

@del_all_wife.got("FLAG", prompt="确定吗? (y/n)")
async def _(matcher: Matcher):
    flag = matcher.state['FLAG'].extract_plain_text().strip()
    if flag.lower() in ['y', 'yes', 'true']:
        for i in wifelist:
            i.unlink(missing_ok=True)
        wifelist.clear()
        await del_all_wife.finish("已删除所有wife.")
    await del_all_wife.finish("操作已取消.")


reset_wife = on_command(
    "重置wife库",
    permission=SUPERUSER,
    priority=5,
    block=True
)

@reset_wife.got("FLAG", prompt="确定吗? (y/n)")
async def _(matcher: Matcher):
    flag = matcher.state['FLAG'].extract_plain_text().strip()
    if flag.lower() in ['y', 'yes', 'true']:
        shutil.rmtree(wifedir)
        shutil.copytree(initial, wifedir)
        wifelist.clear()
        wifelist.extend([ i for i in wifedir.rglob(r'*') ])
        await reset_wife.finish("已重置所有wife.")
    await reset_wife.finish("操作已取消.")


del_wife = on_command(
    "删除wife",
    permission=SUPERUSER,
    priority=5,
    block=True
)

@del_wife.handle()
async def _(
    matcher: Matcher,
    args: Message = CommandArg()
):
    msg: str = args.extract_plain_text()
    if msg:
        matcher.set_arg('ARGS', args)

@del_wife.got("ARGS", prompt="需要wife名")
async def _(args: str = ArgPlainText('ARGS')):
    _file = args.strip()
    if not _file:
        await del_wife.reject()
    file = wifedir / _file
    file.unlink(missing_ok=True)
    clean_list(file)
    await del_wife.finish("已尝试删除1个wife.")


add_wife = on_command(
    "添加wife",
    permission=SUPERUSER,
    priority=5,
    block=True
)

@add_wife.handle()
async def _(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()) -> None:
    if args.extract_plain_text().strip():
        matcher.state["ARGS"] = args
    if contains_image(event):
        matcher.state["IMAGES"] = event

@add_wife.got("ARGS", prompt="名字呢?")
@add_wife.got("IMAGES", prompt="图呢?")
async def _(event: MessageEvent, args: str = ArgPlainText('ARGS')):
    image_urls = get_image_urls(event)
    if not image_urls:
        await add_wife.send("图呢?")
        await add_wife.reject()
    if len(image_urls) > 1:
        await add_wife.finish("一次只能添加一个wife")
    img, status = await image_download(image_urls[0], args.split("\n")[0].strip())
    if not status:
        if img not in wifelist:
            wifelist.append(img)
        await add_wife.finish("添加成功!")
    await add_wife.finish(f"发生错误: {status}")


def contains_image(event: MessageEvent) -> bool:
    message = event.reply.message if event.reply else event.message
    return bool([i for i in message if i.type == "image"])


def get_image_urls(event: MessageEvent) -> List[Tuple[str, str]]:
    message = event.reply.message if event.reply else event.message
    return [
        (i.data["url"], str(i.data["file"]).upper())
        for i in message
        if i.type == "image" and i.data.get("url")
    ]


async def image_download(
    img: Tuple[str, str],
    filename: str
) -> Tuple[Path, str]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    }
    image, sc = Path(), ""
    async with AsyncClient().stream(
        "GET", url = img[0],
        headers=headers,
        follow_redirects=True,
        timeout=30
    ) as res:
        if res.status_code == 200:
            image = wifedir / filename
            with open(image, 'wb') as fd:  # 写入文件
                async for chunk in res.aiter_bytes(1024):
                    fd.write(chunk)
            logger.success(f'获取图片 {img[1]} 成功')
        else:
            logger.error(sc := f'获取图片 {img[1]} 失败: {res.status_code}')
        await res.aclose()
    return image, sc

