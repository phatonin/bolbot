#!/bin/env python3.6

import os
import discord
import dotenv
import re
import perso
import regles

dotenv.load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


class Token:
    WS = re.compile(r'\s*')
    
    def __init__(self, raw, le_perso=None):
        self.raw = raw
    
    @staticmethod
    def _skip_ws(s, pos):
        m = Token.WS.match(s, pos=pos)
        return pos + len(m.group())
        
    @staticmethod
    def tokenize(s, le_perso=None):
        pos = 0
        while pos < len(s):
            pos = Token._skip_ws(s, pos)
            for pat, ctor in Token.PATTERNS:
                m = pat.match(s, pos)
                if m is not None:
                    raw = m.group()
                    args = m.groupdict()
                    pos += len(raw)
                    yield ctor(raw, le_perso=le_perso, **args)
                    break
        

class Mention(Token):
    def __init__(self, raw, le_perso=None, userid=0):
        Token.__init__(self, raw)
        self.userid = int(userid)

class Dice(Token):
    def __init__(self, raw, le_perso=None, dice_number=1, dice_type=6, additional=''):
        Token.__init__(self, raw)
        self.dice_number = int(dice_number)
        self.dice_type = int(dice_type)
        self.bonus = additional.lower().count('b')
        self.malus = additional.lower().count('m')

class Number(Token):
    def __init__(self, raw, le_perso=None, number=0):
        Token.__init__(self, raw)
        self.number = int(number)
        
class Sign(Token):
    def __init__(self, raw, le_perso=None, sign=1):
        Token.__init__(self, raw)
        self.sign = 1 if (sign == '+' or sign >= 0) else -1

class Bonus(Token):
    def __init__(self, raw, le_perso=None):
        Token.__init__(self, raw)

class Malus(Token):
    def __init__(self, raw, le_perso=None):
        Token.__init__(self, raw)

class Difficulte(Token):
    def __init__(self, raw, le_perso=None, difficulte=regles.Difficulte.MOYENNE):
        Token.__init__(self, raw, le_perso=le_perso)
        self.difficulte = difficulte

class Score(Token):
    def __init__(self, raw, le_perso=None, ref=None):
        Token.__init__(self, raw, le_perso=le_perso)
        self.le_perso = le_perso
        self.ref = ref

class Junk(Token):
    def __init__(self, raw, le_perso=None, junk=''):
        Token.__init__(self, raw)
        self.junk = junk

def String(raw, le_perso=None, string=''):
    if string.lower() in regles.Difficulte.MAP:
        return Difficulte(raw, le_perso=le_perso, difficulte=regles.Difficulte.MAP[string])
    if string.lower() in le_perso.ref_map:
        return Score(raw, le_perso=le_perso, ref=le_perso.ref_map[string])
    if string.lower() in le_perso.avantages.value:
        return Bonus(raw, le_perso=le_perso)
    if string.lower() in le_perso.desavantages.value:
        return Malus(raw, le_perso=le_perso)
    if string.lower() == le_perso.nom.value.lower():
        return Score(raw, le_perso=le_perso, ref=le_perso.nom)
    return Junk(raw, le_perso=le_perso, junk=string)

Token.PATTERNS = (
    (
        re.compile(r'<@!(?P<userid>\d+)>', re.RegexFlag.IGNORECASE),
        Mention
    ),
    (
        re.compile(r'(?P<dice_number>\d+)d(?P<dice_type>\d+)(?P<additional>[MB]*)', re.RegexFlag.IGNORECASE),
        Dice
    ),
    (
        re.compile(r'(?P<dice_number>\d+)d(?P<additional>[MB]*)', re.RegexFlag.IGNORECASE),
        Dice
    ),
    (
        re.compile(r'd(?P<dice_type>\d+)(?P<additional>[MB]*)', re.RegexFlag.IGNORECASE),
        Dice
    ),
    (
        re.compile(r'(?P<number>[+-]?\d+)', re.RegexFlag.IGNORECASE),
        Number
    ),
    (
        re.compile(r'(?P<sign>[+-])', re.RegexFlag.IGNORECASE),
        Sign
    ),
    (
        re.compile(r'b(?:onus)', re.RegexFlag.IGNORECASE),
        Bonus
    ),
    (
        re.compile(r'm(?:alus)', re.RegexFlag.IGNORECASE),
        Malus
    ),
    (
        re.compile(r'(?P<string>\w+)', re.RegexFlag.IGNORECASE),
        String
    ),
    (
        re.compile(r'(?P<junk>\S+)', re.RegexFlag.IGNORECASE),
        Junk
    )
)

class TokenVisitor:
    def __init__(self):
        pass
    
    def parse(self, s, le_perso=None):
        self.start()
        for t in Token.tokenize(s, le_perso=le_perso):
            self.visit_token(t)
        return self.finish()
    
    def start(self):
        raise NotImplementedError()
    
    def finish(self):
        raise NotImplementedError()
    
    def visit_token(self, t):
        if isinstance(t, Dice):
            self.visit_dice(t)
        elif isinstance(t, Number):
            self.visit_number(t)
        elif isinstance(t, Mention):
            self.visit_mention(t)
        elif isinstance(t, Sign):
            self.visit_sign(t)
        elif isinstance(t, Junk):
            self.visit_junk(t)
        elif isinstance(t, Bonus):
            self.visit_bonus(t)
        elif isinstance(t, Malus):
            self.visit_malus(t)
        elif isinstance(t, Difficulte):
            self.visit_difficulte(t)
        elif isinstance(t, Score):
            self.visit_score(t)
        else:
            raise RuntimeError()

    def visit_dice(self, t):
        raise NotImplementedError()

    def visit_number(self, t):
        raise NotImplementedError()

    def visit_mention(self, t):
        raise NotImplementedError()

    def visit_sign(self, t):
        raise NotImplementedError()

    def visit_junk(self, t):
        raise NotImplementedError()

    def visit_bonus(self, t):
        raise NotImplementedError()

    def visit_malus(self, t):
        raise NotImplementedError()

    def visit_difficulte(self, t):
        raise NotImplementedError()

    def visit_score(self, t):
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
        
class JetTokenVisitor(TokenVisitor):
    def __init__(self):
        TokenVisitor.__init__(self)
        
    def start(self):
        self.poubelle = []
        self.scores = []
        self.bonus = 0
        self.malus = 0
        self.sign = 1
        
    def finish(self):
        return self.scores, self.bonus, self.malus, self.poubelle

    def visit_dice(self, t):
        self.poubelle.append(t.raw)
        self.sign = 1

    def visit_number(self, t):
        if t.number < 0:
            self.scores.append((-1, perso.Ref(abs(t.number), t.raw)))
        else:
            self.scores.append((self.sign, perso.Ref(t.number, t.raw)))
        self.sign = 1

    def visit_mention(self, t):
        self.sign = 1

    def visit_sign(self, t):
        self.sign = t.sign

    def visit_junk(self, t):
        self.poubelle.append(t.raw)
        self.sign = 1

    def visit_bonus(self, t):
        self.bonus += 1
        self.sign = 1

    def visit_malus(self, t):
        self.malus += 1
        self.sign = 1

    def visit_difficulte(self, t):
        d = t.difficulte
        self.scores.append((d.sign, perso.Ref(d.mod, d.name)))
        self.sign = 1

    def visit_score(self, t):
        if t.ref.name != 'nom':
            if t.ref.is_int():
                self.scores.append((self.sign, t.ref))
            else:
                self.poubelle.append(t.raw)
        self.sign = 1
        
    
class CommandJet(Command):
    MENTION_PATTERN = re.compile(r'^<@!\d+>$')
    
    def __init__(self, client):
        Command.__init__(self, client)

    async def get_reply(self, message):
        if not message.content.startswith('jet'):
            return ()
        persos = self.get_perso(message)
        if len(persos) == 0:
            return (':warning: Qui?',)
        user, le_perso = persos[0]
        scores, bonus, malus, poubelle = JetTokenVisitor().parse(message.content[3:], le_perso)
        sign, mod, dice, result, reussite = regles.jet(scores, bonus, malus)
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
