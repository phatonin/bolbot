#!/bin/env python3.6

import os
import discord
import dotenv
import re
import perso
import regles

dotenv.load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class Command:
    def __init__(self, client):
        self.client = client

    async def get_reply(self, message):
        raise NotImplementedError()

class CommandLance(Command):
    DICE_PATTERN = re.compile(r'^(?P<n>[12]?)d(?P<d>[36]?)\s*(?P<k>[MB]*)\s*(?:(?P<s>[+-])\s*(?P<m>\d+))?$', re.RegexFlag.IGNORECASE)
    DIGITS = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine')

    def __init__(self, client):
        Command.__init__(self, client)
        
    async def get_reply(self, message):
        r = CommandLance.parse_des(message.content)
        if r is None:
            return None
        dice, _, result = regles.lance(**r)
        return f'{message.author.mention} lance `{message.content}`\n{CommandLance.dice_icons(dice)}\n**{result}**'

    @staticmethod
    def parse_des(expr):
        m = BoLClient.DICE_PATTERN.match(expr)
        if m is not None:
            return {
                'number_read': 1 if m.group('n') == '' else int(m.group('n')),
                'dice_type': 6 if m.group('d') == '' else int(m.group('d')),
                'bonus': m.group('k').count('B'),
                'malus': m.group('k').count('M'),
                'sign': 1 if m.group('s') is None or m.group('s') == '+' else -1,
                'mod': 0 if m.group('m') is None else int(m.group('m'))
            }
        return None

    @staticmethod    
    def dice_icons(dice):
        return ' '.join(f':{BoLClient.DIGITS[n]}:' for n in dice)

class CommandPurge(Command):
    def __init__(self, client):
        Command.__init__(self, client)
        
    async def get_reply(self, message):
        if message.content != 'purge':
            return None
        await message.channel.delete_messages(self.client.message_queue)
        n = len(self.client.message_queue)
        self.message_queue = []
        return ':x: Purged {n} messages'

class BoLClient(discord.Client):
    def __init__(self, pj_path):
        discord.Client.__init__(self)
        self.message_queue = []
        self.pj_par_userid = {}
        self.persos_par_nom = {}
        for pj, path in perso.load(pj_path):
            userid = int(os.path.basename(path)[:-4])
            self.pj_par_userid[userid] = pj
            self.persos_par_nom[pj.nom] = pj
        self.commands = tuple(ctor(self) for ctor in (CommandLance, CommandPurge))
        
    async def on_ready(self):
        print (f'{self.user} has connected to Discord!')
    
    async def on_error(self, event, *args, **_):
        if event == 'on_message':
            print (f'Unhandled message: {args[0]}')
        raise
    
    def get_perso(self, message):
        result = []
        for t in message.content.lower().split():
            if t in self.persos_par_nom:
                result.append((None, self.persos_par_nom[t]))
        for user in message.mentions:
            if user.id in self.pj_par_userid:
                result.append((user, self.pj_par_userid[user.id]))
        if len(result) == 0 and message.author.id in self.pj_par_userid:
            result.append((message.author, self.pj_par_userid[message.author.id]))
        return result
    
    def str_sign(self, n):
        if n == 1:
            return '+'
        if n == -1:
            return '-'
        
    def perso_label(self, p, user):
        if user is None:
            return f'**{p.nom}**'
        return f'**{p.nom}** ({user.mention})'
    
    async def reply(self, message, content):
        r = await message.channel.send(content)
        self.message_queue.append(r)
        
    async def on_message(self, message):
        if message.author.bot:
            return
        r = self.parse_des(message.content)
        if r is not None:
            self.message_queue.append(message)
            dice, _, result = regles.lance(**r)
            await self.reply(message, f'{message.author.mention} lance `{message.content}`\n{self.dice_icons(dice)}\n**{result}**')
        elif message.content == 'purge':
            self.message_queue.append(message)
            await message.channel.delete_messages(self.message_queue)
            self.message_queue = []
        elif message.content.startswith('fdp'):
            self.message_queue.append(message)
            persos = self.get_perso(message)
            for user, p in persos:
                await self.reply(message, f'Fiche de perso de {self.perso_label(p, user)}\n{p.fiche()}')
            if len(persos) == 0:
                await self.reply(message, f'Qui?')
        elif message.content.startswith('jet'):
            self.message_queue.append(message)
            persos = self.get_perso(message)
            if len(persos) == 0:
                await self.reply(message, f'Qui?')
            else:
                user, le_perso = persos[0]
                scores, bonus, malus, poubelle, sign, mod, dice, result, reussite = regles.jet(le_perso, message.content.split()[1:])
                score_noms = ' '.join(f'{self.str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
                score_valeurs = ' '.join(f'{self.str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
                cont = f'{self.perso_label(le_perso, user)} fait un jet de ` {score_noms} ({score_valeurs} = {self.str_sign(sign)}{mod})`'
                if bonus > 0:
                    cont += f' avec {bonus} dé{"" if bonus == 1 else "s"} de bonus'
                if malus > 0:
                    cont += f' {"et" if malus > 0 else "avec"} {malus} dé{"" if malus == 1 else "s"} de malus'
                if poubelle:
                    cont += f' (inconnus: {", ".join(poubelle)})'
                cont += f'\n{self.dice_icons(dice)}\n'
                cont += f'**{result}** **{reussite.name.capitalize()}**'
                await self.reply(message, cont)
        else:
            print (f'{message}\n    {message.content}')

client = BoLClient('data/PJ')
print (client.persos_par_nom)
print (client.pj_par_userid)
client.run(TOKEN)
