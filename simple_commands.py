#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Telegram bot to play UNO in group chats
# Copyright (c) 2016 Jannes Höke <uno@jhoeke.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from telegram import ParseMode, Update
from telegram.ext import CommandHandler, CallbackContext

from user_setting import UserSetting
from utils import send_async
from shared_vars import dispatcher
from internationalization import _, user_locale

@user_locale
def help_handler(update: Update, context: CallbackContext):
    """Handler for the /help command"""
    help_text = _("游戏指引：\n"
                  "\n"
                  "1. 将这个 Bot 加进一个群\n"
                  "2. 在这个群中，您可以使用 /new 创建一个新游戏，或者使用 /join 加入一个现有的"
                  "游戏\n"
                  "3. 当有最少两名玩家加入后，请使用 /start 开始游戏\n"
                  "4. 在聊天框中输入 <code>@unobot</code> 并按空格键，或者点击信息旁边的 "
                  "<code>via @unobot</code> 。您就可以看到您的手牌，以及一些像抽牌这样的选项， "
                  "<b>?</b> 选项用来查看当前游戏状态。 <b>灰色的牌</b> 是您当前 <b>不可以</b> 打"
                  "出的。请选择其中的一个选项。\n"
                  "玩家随时可以加入游戏，如果想要离开当前的游戏，请输入 /leave 。如果玩家超过 "
                  "90 秒没有出牌，您可以使用 /skip 跳过这个玩家\n"
                  "\n"
                  "<b>语言</b> 和其他设置： /settings \n"
                  "其他命令（仅限游戏创建者使用）\n"
                  "/close - 不允许其他人中途加入\n"
                  "/open - 允许其他人中途加入\n"
                  "/enable_translations - 翻译文本给游戏中所有使用不同语言的玩家\n"
                  "/disable_translations - 关闭翻译并使用英文\n"
                  "\n"
                  "<b>实验性功能：</b> 玩家可以同时在多个群组中进行游戏。点击 <code>当前游"
                  "戏： ...</code> 按钮然后选择您想在哪个群组玩。\n"
                  "如果喜欢这个机器人， 请给机器人 <a href=\"https://telegram.me/storebot?"
                  "start=mau_mau_bot\">评分</a> ，订阅 <a href=\"https://telegram.me/"
                  "unobotupdates\"> 更新频道</a> 获取最新消息，并买一副 UNO 牌。")

    send_async(context.bot, update.message.chat_id, text=help_text,
               parse_mode=ParseMode.HTML, disable_web_page_preview=True)

@user_locale
def modes(update: Update, context: CallbackContext):
    """Handler for the /help command"""
    modes_explanation = _("本机器人有三种游戏模式: 传统、Sanic 及野性 (Wild) 模式。\n"
        " 🎻 传统模式使用常见的 UNO 卡组，且不会自动跳过。\n"
        " 🚀 Sanic 模式使用常见的 UNO 卡组，且机器人会自动跳过闲置过久的玩家。\n"
        " 🐉 野性 (Wild) 模式使用功能牌较多、数字牌较少的卡组，并且不会自动跳过。\n"
        "\n"
        "如果要切换游戏模式，游戏创建者必须输入机器人的使用者名称 + 空格，就像玩游戏那"
        "样，之后将显示出所有游戏模式选项以供选择。")
    send_async(context.bot, update.message.chat_id, text=modes_explanation,
               parse_mode=ParseMode.HTML, disable_web_page_preview=True)

@user_locale
def source(update: Update, context: CallbackContext):
    """Handler for the /help command"""
    source_text = _("来源:\n"
      "抽牌图标来自 <a href=\\http://www.faithtoken.com/\\>Faithtoken</\n"
      "a>。\n"
      "跳过图标來自 <a href=\\http://delapouite.com/\\>Delapouite</a>。\n"
      "原始图标可在 http://game-icons.net 获取。\n"
      "图标由 ɳick 编辑")

    send_async(context.bot, update.message.chat_id, text=source_text + '\n' +
                                                 attributions,
               parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@user_locale
def news(update: Update, context: CallbackContext):
    """Handler for the /news command"""
    send_async(context.bot, update.message.chat_id,
               text=_("查看机器人的所有更新: https://telegram.me/unobotupdates"),
               disable_web_page_preview=True)


@user_locale
def stats(update: Update, context: CallbackContext):
    user = update.message.from_user
    us = UserSetting.get(id=user.id)
    if not us or not us.stats:
        send_async(context.bot, update.message.chat_id,
                   text=_("您并没有启用数据统计。请私聊我发送 /settings 进行设置。"))
    else:
        stats_text = list()

        n = us.games_played
        stats_text.append(
            _("玩了 {number} 盘",
              "玩了 {number} 盘",
              n).format(number=n)
        )

        n = us.first_places
        m = round((us.first_places / us.games_played) * 100) if us.games_played else 0
        stats_text.append(
            _("赢了 {number} 盘 ({percent}%)",
              "赢了 {number} 盘 ({percent}%)",
              n).format(number=n, percent=m)
        )

        n = us.cards_played
        stats_text.append(
            _("总共出过 {number} 张牌",
              "总共出过 {number} 张牌",
              n).format(number=n)
        )

        send_async(context.bot, update.message.chat_id,
                   text='\n'.join(stats_text))


def register():
    dispatcher.add_handler(CommandHandler('help', help_handler))
    dispatcher.add_handler(CommandHandler('source', source))
    dispatcher.add_handler(CommandHandler('news', news))
    dispatcher.add_handler(CommandHandler('stats', stats))
    dispatcher.add_handler(CommandHandler('modes', modes))
