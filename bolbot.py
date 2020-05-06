#!/bin/env python3.6

import os
import discord
import dotenv
import re
import perso
import regles

dotenv.load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

@client.event
async def on_ready():
    print (f'{client.user} has connected to Discord!')

@client.event
async def on_error(event, *args, **kwargs):
    if event == 'on_message':
        print (f'Unhandled message: {args[0]}')
    raise


DICE_PATTERN = re.compile(r'^(?P<n>[12]?)d(?P<d>[36]?)\s*(?P<k>[MB]*)\s*(?:(?P<s>[+-])\s*(?P<m>\d+))?$', re.RegexFlag.IGNORECASE)
def parse_des(expr):
    m = DICE_PATTERN.match(expr)
    if m is not None:
        return {
            'number_read': 1 if m.group('n') == '' else int(m.group('n')),
            'dice_type': 6 if m.group('d') == '' else int(m.group('d')),
            'skip_low': m.group('k').count('B'),
            'skip_high': m.group('k').count('M'),
            'sign': 1 if m.group('s') is None or m.group('s') == '+' else -1,
            'mod': 0 if m.group('m') is None else int(m.group('m'))
        }
    return None

MESSAGE_QUEUE = []

DIGITS = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine')
def dice_icons(dice):
    return ' '.join(f':{DIGITS[n]}:' for n in dice)

def get_user(message):
    if len(message.mentions) == 0:
        return message.author
    if len(message.mentions) == 1:
        return message.mentions[0]
    return None

def get_perso(message):
    result = []
    for p in perso.TOUS.values():
        if p.nom.value in message.content:
            result.append((None, p))
    for user in message.mentions:
        if user.id in perso.PJ:
            result.append((user, perso.PJ[user.id]))
    if len(result) == 0 and message.author.id in perso.PJ:
        result.append((message.author, perso.PJ[message.author.id]))
    return result

def str_sign(n):
    if n == 1:
        return '+'
    if n == -1:
        return '-'
@client.event
async def on_message(message):
    global MESSAGE_QUEUE
    if message.author.bot:
        return
    r = parse_des(message.content)
    if r is not None:
        dice, sorted_dice, result = regles.lance(**r)
        reply = await message.channel.send(f'{message.author.mention} lance `{message.content}`\n{dice_icons(dice)}\n**{result}**')
        MESSAGE_QUEUE.extend([message, reply])
    elif message.content == 'purge':
        MESSAGE_QUEUE.append(message)
        await message.channel.delete_messages(MESSAGE_QUEUE)
        MESSAGE_QUEUE = []
    elif message.content.startswith('fdp'):
        MESSAGE_QUEUE.append(message)
        persos = get_perso(message)
        for user, p in persos:
            if user is None:
                label = f'**{p.nom}**'
            else:
                label = f'**{p.nom}** ({user.mention})'
            reply = await message.channel.send(f'Fiche de perso de {label}\n{p.fiche()}')
            MESSAGE_QUEUE.append(reply)
        if len(persos) == 0:
            reply = await message.channel.send(f'Qui?')
            MESSAGE_QUEUE.append(reply)
    elif message.content.startswith('jet'):
        user = get_user(message)
        if user is not None and user.id in perso.PJ:
            le_perso = perso.PJ[user.id]
            scores, bonus, malus, poubelle, sign, mod, dice, result, reussite = regles.jet(le_perso, message.content.split()[1:])
            score_noms = ' '.join(f'{str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
            score_valeurs = ' '.join(f'{str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
            cont = f'*{le_perso.nom}* ({user.mention}) fait un jet de ` {score_noms} ({score_valeurs} = {str_sign(sign)}{mod})`'
            if bonus > 0:
                cont += f' avec {bonus} dé{"" if bonus == 1 else "s"} de bonus'
            if malus > 0:
                cont += f' {"et" if malus > 0 else "avec"} {malus} dé{"" if malus == 1 else "s"} de malus'
            if poubelle:
                cont += f' (inconnus: {", ".join(poubelle)})'
            cont += f'\n{dice_icons(dice)}\n'
            cont += f'**{result}** **{reussite.name.capitalize()}**'
            reply = await message.channel.send(cont)
            MESSAGE_QUEUE.extend([message, reply])
    else:
        print (f'{message}\n    {message.content}')
            
perso.load_pjs()
print (perso.TOUS)
print (perso.PJ)
client.run(TOKEN)
