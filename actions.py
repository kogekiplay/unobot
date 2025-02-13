import random

import logging

import card as c
from datetime import datetime

from telegram import Message, Chat
from telegram.ext import CallbackContext
from apscheduler.jobstores.base import JobLookupError

from config import TIME_REMOVAL_AFTER_SKIP, MIN_FAST_TURN_TIME
from errors import DeckEmptyError, NotEnoughPlayersError
from internationalization import __, _
from shared_vars import gm
from user_setting import UserSetting
from utils import send_async, display_name, game_is_running

logger = logging.getLogger(__name__)

class Countdown(object):
    player = None
    job_queue = None

    def __init__(self, player, job_queue):
        self.player = player
        self.job_queue = job_queue


# TODO do_skip() could get executed in another thread (it can be a job), so it looks like it can't use game.translate?
def do_skip(bot, player, job_queue=None):
    game = player.game
    chat = game.chat
    skipped_player = game.current_player
    next_player = game.current_player.next

    if skipped_player.waiting_time > 0:
        skipped_player.anti_cheat += 1
        skipped_player.waiting_time -= TIME_REMOVAL_AFTER_SKIP
        if (skipped_player.waiting_time < 0):
            skipped_player.waiting_time = 0

        try:
            skipped_player.draw()
        except DeckEmptyError:
            pass

        n = skipped_player.waiting_time
        send_async(bot, chat.id,
                   text=__("该玩家的等待时间已降至 {time} 秒。\n"
                        "轮到： {name}", multi=game.translate)
                   .format(time=n,
                           name=display_name(next_player.user))
        )
        logger.info("{player} 已被跳过！ "
                    .format(player=display_name(player.user)))
        game.turn()
        if job_queue:
            start_player_countdown(bot, game, job_queue)

    else:
        try:
            gm.leave_game(skipped_player.user, chat)
            send_async(bot, chat.id,
                       text=__("{name1} 已经连续4次没有出牌，将其移出了游戏。\n "
                            "轮到： {name2}", multi=game.translate)
                       .format(name1=display_name(skipped_player.user),
                               name2=display_name(next_player.user)))
            logger.info("{player} 已被跳过！ "
                    .format(player=display_name(player.user)))
            if job_queue:
                start_player_countdown(bot, game, job_queue)

        except NotEnoughPlayersError:
            send_async(bot, chat.id,
                       text=__("{name} 已经被连续跳过了 4 次。\n"
                               "游戏结束。", multi=game.translate)
                       .format(name=display_name(skipped_player.user)))

            gm.end_game(chat, skipped_player.user)



def do_play_card(bot, player, result_id):
    """Plays the selected card and sends an update to the group if needed"""
    card = c.from_str(result_id)
    player.play(card)
    game = player.game
    chat = game.chat
    user = player.user

    us = UserSetting.get(id=user.id)
    if not us:
        us = UserSetting(id=user.id)

    if us.stats:
        us.cards_played += 1

    if game.choosing_color:
        send_async(bot, chat.id, text=__("请选择颜色", multi=game.translate))

    if len(player.cards) == 1:
        send_async(bot, chat.id, text="UNO!")

    if len(player.cards) == 0:
        send_async(bot, chat.id,
                   text=__("{name} 赢了！", multi=game.translate)
                   .format(name=user.first_name))

        if us.stats:
            us.games_played += 1

            if game.players_won is 0:
                us.first_places += 1

        game.players_won += 1

        try:
            gm.leave_game(user, chat)
        except NotEnoughPlayersError:
            send_async(bot, chat.id,
                       text=__("游戏结束！", multi=game.translate))

            us2 = UserSetting.get(id=game.current_player.user.id)
            if us2 and us2.stats:
                us2.games_played += 1

            gm.end_game(chat, user)


def do_draw(bot, player):
    """Does the drawing"""
    game = player.game
    draw_counter_before = game.draw_counter

    try:
        player.draw()
    except DeckEmptyError:
        send_async(bot, player.game.chat.id,
                   text=__("牌堆中已经没有更多的牌了。",
                           multi=game.translate))

    if (game.last_card.value == c.DRAW_TWO or
        game.last_card.special == c.DRAW_FOUR) and \
            draw_counter_before > 0:
        game.turn()


def do_call_bluff(bot, player):
    """Handles the bluff calling"""
    game = player.game
    chat = game.chat

    if player.prev.bluffing:
        send_async(bot, chat.id,
                   text=__("质疑成功！给 {name} 4 张牌",
                           multi=game.translate)
                   .format(name=player.prev.user.first_name))

        try:
            player.prev.draw()
        except DeckEmptyError:
            send_async(bot, player.game.chat.id,
                       text=__("牌堆中已经没有更多的牌了。",
                               multi=game.translate))

    else:
        game.draw_counter += 2
        send_async(bot, chat.id,
                   text=__("质疑 {name1} 失败！给 {name2} 6 张牌",
                           multi=game.translate)
                   .format(name1=player.prev.user.first_name,
                           name2=player.user.first_name))
        try:
            player.draw()
        except DeckEmptyError:
            send_async(bot, player.game.chat.id,
                       text=__("牌堆中已经没有更多的牌了。",
                               multi=game.translate))

    game.turn()


def start_player_countdown(bot, game, job_queue):
    player = game.current_player
    time = player.waiting_time

    if time < MIN_FAST_TURN_TIME:
        time = MIN_FAST_TURN_TIME

    if game.mode == 'fast':
        if game.job:
            try:
                game.job.schedule_removal()
            except JobLookupError:
                pass

        job = job_queue.run_once(
            #lambda x,y: do_skip(bot, player),
            skip_job,
            time,
            context=Countdown(player, job_queue)
        )

        logger.info("Started countdown for player: {player}. {time} seconds."
                    .format(player=display_name(player.user), time=time))
        player.game.job = job


def skip_job(context: CallbackContext):
    player = context.job.context.player
    game = player.game
    if game_is_running(game):
        job_queue = context.job.context.job_queue
        do_skip(context.bot, player, job_queue)
