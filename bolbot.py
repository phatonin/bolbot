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
    DIGITS = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine')

    def __init__(self, client):
        self.client = client

    async def get_reply(self, message):
        raise NotImplementedError()
    
    def get_perso(self, message):
        result = []
        for t in message.content.lower().split():
            if t in self.client.persos_par_nom:
                result.append((None, self.client.persos_par_nom[t]))
        for user in message.mentions:
            if user.id in self.client.pj_par_userid:
                result.append((user, self.client.pj_par_userid[user.id]))
        if len(result) == 0 and message.author.id in self.client.pj_par_userid:
            result.append((message.author, self.client.pj_par_userid[message.author.id]))
        return result
        
    @staticmethod
    def perso_label(p, user):
        if user is None:
            return f'**{p.nom}**'
        return f'**{p.nom}** ({user.mention})'

    @staticmethod    
    def str_sign(n):
        if n == 1:
            return '+'
        if n == -1:
            return '-'

    @staticmethod    
    def dice_icons(dice):
        return ' '.join(f':{Command.DIGITS[n]}:' for n in dice)

class CommandLance(Command):
    DICE_PATTERN = re.compile(r'^(?P<n>[12]?)d(?P<d>[36]?)\s*(?P<k>[MB]*)\s*(?:(?P<s>[+-])\s*(?P<m>\d+))?$', re.RegexFlag.IGNORECASE)

    def __init__(self, client):
        Command.__init__(self, client)
        
    async def get_reply(self, message):
        r = CommandLance.parse_des(message.content)
        if r is None:
            return ()
        dice, _, result = regles.lance(**r)
        return (f'{message.author.mention} lance `{message.content}`\n{Command.dice_icons(dice)}\n**{result}**',)

    @staticmethod
    def parse_des(expr):
        m = CommandLance.DICE_PATTERN.match(expr)
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

class CommandPurge(Command):
    def __init__(self, client):
        Command.__init__(self, client)
        
    async def get_reply(self, message):
        if message.content != 'purge':
            return ()
        await message.channel.delete_messages(self.client.message_queue)
        n = len(self.client.message_queue)
        self.client.message_queue = []
        return (f':x: {n} messages supprimés',)

class CommandFDP(Command):
    def __init__(self, client):
        Command.__init__(self, client)
        
    async def get_reply(self, message):
        if not message.content.startswith('fdp'):
            return ()
        persos = self.get_perso(message)
        if len(persos) == 0:
            return (':warning: Qui?',)
        return tuple(f'Fiche de perso de {Command.perso_label(p, user)}\n{p.fiche()}' for user, p in persos)

class CommandJet(Command):
    MENTION_PATTERN = re.compile(r'^<@!\d+>$')
    
    def __init__(self, client):
        Command.__init__(self, client)
        
    def ok_token(self, token):
        if CommandJet.MENTION_PATTERN.match(token):
            return False
        if token.lower() in self.client.persos_par_nom:
            return False
        return True
    
    def tokenize(self, message):
        for t in message.content.split()[1:]:
            if self.ok_token(t):
                yield t
        
    async def get_reply(self, message):
        if not message.content.startswith('jet'):
            return ()
        persos = self.get_perso(message)
        if len(persos) == 0:
            return (':warning: Qui?',)
        user, le_perso = persos[0]
        scores, bonus, malus, poubelle, sign, mod, dice, result, reussite = regles.jet(le_perso, self.tokenize(message))
        score_noms = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
        score_valeurs = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
        cont = f'{Command.perso_label(le_perso, user)} fait un jet de ` {score_noms} ({score_valeurs} = {Command.str_sign(sign)}{mod})`'
        if bonus > 0:
            cont += f' avec {bonus} dé{"" if bonus == 1 else "s"} de bonus'
        if malus > 0:
            cont += f' {"et" if malus > 0 else "avec"} {malus} dé{"" if malus == 1 else "s"} de malus'
        if poubelle:
            cont += f' (inconnus: {", ".join(poubelle)})'
        cont += f'\n{Command.dice_icons(dice)}\n'
        cont += f'**{result}** **{reussite.name.capitalize()}**'
        return (cont,)

class BoLClient(discord.Client):
    def __init__(self, pj_path):
        discord.Client.__init__(self)
        self.message_queue = []
        self.pj_par_userid = {}
        self.persos_par_nom = {}
        for pj, path in perso.load(pj_path):
            userid = int(os.path.basename(path)[:-4])
            self.pj_par_userid[userid] = pj
            self.persos_par_nom[pj.nom.value.lower()] = pj
        self.commands = tuple(ctor(self) for ctor in (CommandLance, CommandPurge, CommandFDP, CommandJet))
        
    async def on_ready(self):
        print (f'{self.user} has connected to Discord!')
    
    async def on_error(self, event, *args, **_):
        if event == 'on_message':
            print (f'Unhandled message: {args[0]}')
        raise
    
    async def reply(self, message, content):
        r = await message.channel.send(content)
        self.message_queue.append(r)
        
    async def on_message(self, message):
        if message.author.bot:
            return
        for cmd in self.commands:
            contents = await cmd.get_reply(message)
            if len(contents) > 0:
                self.message_queue.append(message)
                for content in contents:
                    reply = await message.channel.send(content)
                    self.message_queue.append(reply)
                break
        else:
            print (f'{message}\n    {message.content}')

client = BoLClient('data/PJ')
print (client.persos_par_nom)
print (client.pj_par_userid)
client.run(TOKEN)
