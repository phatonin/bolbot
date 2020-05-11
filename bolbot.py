#!/bin/env python3.6

import os
import discord
import dotenv
import re
import perso
import regles

dotenv.load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


class Parser:
    WS = re.compile(r'\s*')
    PATTERNS = (
        (
            re.compile(r'<@!(?P<userid>\d+)>', re.RegexFlag.IGNORECASE),
            'mention'
        ),
        (
            re.compile(r'(?P<dice_number>\d+)d(?P<dice_type>\d+)(?P<additional>[MB]*)', re.RegexFlag.IGNORECASE),
            'dice'
        ),
        (
            re.compile(r'(?P<dice_number>\d+)d(?P<additional>[MB]*)', re.RegexFlag.IGNORECASE),
            'dice'
        ),
        (
            re.compile(r'd(?P<dice_type>\d+)(?P<additional>[MB]*)', re.RegexFlag.IGNORECASE),
            'dice'
        ),
        (
            re.compile(r'(?P<number>[+-]?\d+)', re.RegexFlag.IGNORECASE),
            'number'
        ),
        (
            re.compile(r'(?P<sign>[+-])', re.RegexFlag.IGNORECASE),
            'sign'
        ),
        (
            re.compile(r'b(?:onus)', re.RegexFlag.IGNORECASE),
            'bonus'
        ),
        (
            re.compile(r'm(?:alus)', re.RegexFlag.IGNORECASE),
            'malus'
        ),
        (
            re.compile(r'(?P<string>\w+)', re.RegexFlag.IGNORECASE),
            'string'
        ),
        (
            re.compile(r'(?P<junk>\S+)', re.RegexFlag.IGNORECASE),
            'junk'
        )
    )

    def __init__(self, le_perso=None):
        self.le_perso = le_perso
    
    @staticmethod
    def _skip_ws(s, pos):
        m = Parser.WS.match(s, pos=pos)
        return pos + len(m.group())
        
    def parse(self, s):
        pos = 0
        while pos < len(s):
            pos = Parser._skip_ws(s, pos)
            for pat, meth in Parser.PATTERNS:
                m = pat.match(s, pos)
                if m is not None:
                    raw = m.group()
                    args = m.groupdict()
                    pos += len(raw)
                    getattr(self, '_' + meth)(raw, **args)
                    break
        return self.finish()
                
    def _mention(self, raw, userid):
        self.mention(raw, int(userid))
    
    def mention(self, raw, userid):
        raise NotImplementedError()
    
    def _dice(self, raw, dice_number=1, dice_type=6, additional=''):
        ladditional = additional.lower()
        self.dice(raw, int(dice_number), int(dice_type), ladditional.count('b'), ladditional.count('m'))
        
    def dice(self, raw, dice_number, dice_type, bonus, malus):
        raise NotImplementedError()
    
    def _number(self, raw, number):
        self.number(raw, int(number))
        
    def number(self, raw, number):
        raise NotImplementedError()
        
    def _sign(self, raw, sign):
        if sign == '+':
            self.sign(raw, 1)
        elif sign == '-':
            self.sign(raw, -1)
    
    def sign(self, raw, sign):
        raise NotImplementedError()
    
    def _bonus(self, raw):
        self.bonus(raw)
        
    def _malus(self, raw):
        self.malus(raw)
        
    def bonus(self, raw):
        raise NotImplementedError()
    
    def malus(self, raw):
        raise NotImplementedError()
    
    def _junk(self, raw):
        self.junk(raw)
        
    def junk(self, raw):
        raise NotImplementedError()
    
    def _string(self, raw, string):
        if string.lower() in regles.Difficulte.MAP:
            self.difficulte(raw, regles.Difficulte.MAP[string])
        elif self.le_perso is not None:
            if string.lower() in self.le_perso.ref_map:
                self.score(raw, self.le_perso.ref_map[string])
            elif string.lower() in self.le_perso.avantages.value:
                self.bonus(raw)
            elif string.lower() in self.le_perso.desavantages.value:
                self.malus(raw)
            else:
                self.junk(raw)
        else:
            self.junk(raw)

    def difficulte(self, raw, difficulte):
        raise NotImplementedError()
    
    def score(self, raw, ref):
        raise NotImplementedError()
    
    def finish(self):
        raise NotImplementedError()

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
    def perso_label(p, userid):
        if userid is None:
            return f'**{p.nom}**'
        if p is None:
            return f'<@!{userid}>'
        return f'**{p.nom}** (<@!{userid}>)'

    @staticmethod    
    def str_sign(n):
        if n == 1:
            return '+'
        if n == -1:
            return '-'

    @staticmethod    
    def dice_icons(dice):
        return ' '.join(f':{Command.DIGITS[n]}:' for n in dice)

class LanceJetParser(Parser):
    def __init__(self, client, userid):
        Parser.__init__(self)
        self.poubelle = []
        self.scores = []
        self.current_sign = 1
        self.client = client
        self.userid = None
        self.mention(str(userid), userid)

    def number(self, raw, number):
        if number < 0:
            self.scores.append((-1, perso.Ref(abs(number), raw)))
        else:
            self.scores.append((self.current_sign, perso.Ref(number, raw)))
        self.current_sign = 1

    def mention(self, raw, userid):
        self.userid = userid
        if userid in self.client.pj_par_userid:
            self.le_perso = self.client.pj_par_userid[userid]
        self.current_sign = 1

    def sign(self, raw, sign):
        self.current_sign = sign

    def junk(self, raw):
        if raw.lower() in self.client.persos_par_nom:
            self.le_perso = self.client.persos_par_nom[raw.lower()]
        else:
            self.poubelle.append(raw)
        self.current_sign = 1

    def difficulte(self, raw, difficulte):
        self.scores.append((difficulte.sign, perso.Ref(difficulte.mod, difficulte.name)))
        self.current_sign = 1

    def score(self, raw, ref):
        if ref.name != 'nom':
            if ref.is_int():
                self.scores.append((self.current_sign, ref))
            else:
                self.poubelle.append(raw)
        self.current_sign = 1

class LanceParser(LanceJetParser):
    def __init__(self, client, userid):
        LanceJetParser.__init__(self, client, userid)
        self.lance = (None, None, None)
        self.des = None
        
    def finish(self):
        return self.lance, self.des, self.scores, self.poubelle

    def dice(self, raw, dice_number, dice_type, bonus, malus):
        if self.des is None:
            self.lance = regles.lance(dice_number, dice_type, bonus, malus)
            self.des = raw
        else:
            self.poubelle.append(raw)
        self.current_sign = 1

    def bonus(self, raw):
        self.poubelle.append(raw)
        self.current_sign = 1

    def malus(self, raw):
        self.poubelle.append(raw)
        self.current_sign = 1

class CommandLance(Command):
    DICE_PATTERN = re.compile(r'^(?P<n>[12]?)d(?P<d>[36]?)\s*(?P<k>[MB]*)\s*(?:(?P<s>[+-])\s*(?P<m>\d+))?$', re.RegexFlag.IGNORECASE)

    def __init__(self, client):
        Command.__init__(self, client)
        
    async def get_reply(self, message):
        if not message.content.startswith('lance'):
            return ()
        parser = LanceParser(self.client, message.author.id)
        (dice, _sorted_dice, result), des, scores, poubelle = parser.parse(message.content[5:])
        if parser.dice is None:
            return (':warning: Lance quoi?',)
        score_total, sign, mod = regles.sum_scores(scores)
        final = result + score_total
        score_noms = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
        score_valeurs = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
        cont = f'{Command.perso_label(parser.le_perso, parser.userid)} lance `{des} {score_noms} ({score_valeurs} = {Command.str_sign(sign)}{mod})`'
        if poubelle:
            cont += f' (inconnus: {", ".join(poubelle)})'
        cont += f'\n{Command.dice_icons(dice)}\n'
        cont += f'**{final}**'
        return (cont,)

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
        
class JetParser(LanceJetParser):
    def __init__(self, client, userid):
        LanceJetParser.__init__(self, client, userid)
        self.n_bonus = 0
        self.n_malus = 0
        
    def finish(self):
        return self.scores, self.n_bonus, self.n_malus, self.poubelle

    def dice(self, raw, dice_number, dice_type, bonus, malus):
        self.poubelle.append(raw)
        self.current_sign = 1

    def bonus(self, raw):
        self.n_bonus += 1
        self.current_sign = 1

    def malus(self, raw):
        self.n_malus += 1
        self.current_sign = 1
    
class CommandJet(Command):
    MENTION_PATTERN = re.compile(r'^<@!\d+>$')
    
    def __init__(self, client):
        Command.__init__(self, client)

    async def get_reply(self, message):
        if not message.content.startswith('jet'):
            return ()
        parser = JetParser(self.client, message.author.id)
        scores, bonus, malus, poubelle = parser.parse(message.content[3:])
        if parser.le_perso is None:
            return (':warning: Qui?',)
        sign, mod, dice, result, reussite = regles.jet(scores, bonus, malus)
        score_noms = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
        score_valeurs = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
        cont = f'{Command.perso_label(parser.le_perso, parser.userid)} fait un jet de ` {score_noms} ({score_valeurs} = {Command.str_sign(sign)}{mod})`'
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
