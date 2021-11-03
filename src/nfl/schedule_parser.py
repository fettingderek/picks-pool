import csv
import os
import sys
from typing import List

import datetime
from dateutil import tz

from dataclasses import dataclass
from html.parser import HTMLParser

PROJECT_DIR = '/Users/derek/workspace/picks-pool'


def get_team_abbr(team_name: str) -> str:
    return {
        '49ers': 'SF',
        'Bears': 'CHI',
        'Bengals': 'CIN',
        'Bills': 'BUF',
        'Broncos': 'DEN',
        'Browns': 'CLE',
        'Buccaneers': 'TB',
        'Cardinals': 'ARI',
        'Chargers': 'LAC',
        'Chiefs': 'KC',
        'Colts': 'IND',
        'Cowboys': 'DAL',
        'Dolphins': 'MIA',
        'Eagles': 'PHI',
        'Falcons': 'ATL',
        'Giants': 'NYG',
        'Jaguars': 'JAX',
        'Jets': 'NYJ',
        'Lions': 'DET',
        'Packers': 'GB',
        'Panthers': 'CAR',
        'Patriots': 'NE',
        'Raiders': 'LV',
        'Rams': 'LAR',
        'Ravens': 'BAL',
        'Saints': 'NO',
        'Seahawks': 'SEA',
        'Steelers': 'PIT',
        'Texans': 'HOU',
        'Titans': 'TEN',
        'Vikings': 'MIN',
        'Washington': 'WSH'
    }.get(team_name)


@dataclass
class Node:
    tag: str
    attrs: list
    data: str

    def has_class(self, class_name: str) -> bool:
        for attr in self.attrs:
            if attr[0] == 'class' and class_name in attr[1].split(' '):
                return True
        return False

    def id(self) -> str:
        return self.get_attr('id')

    def get_attr(self, attr_name: str):
        for attr in self.attrs:
            if attr[0] == attr_name:
                return attr[1]
        return ''


class GameData:
    def __init__(self, week: int):
        self.week = week
        self.game_id: str = ''
        self.date_and_time: str = ''
        self.away_team_name: str = ''
        self.away_team_abbr: str = ''
        self.home_team_name: str = ''
        self.home_team_abbr: str = ''
        self.line: str = ''

    def get_away_team_line(self):
        if self.line == 'EVEN':
            return 0
        line_parts = self.line.split(' ')
        if line_parts[0] == self.away_team_abbr:
            return line_parts[1]
        return -1 * float(line_parts[1])

    def convert_to_local_date(self):
        if self.date_and_time == '':
            print('Unable to parse empty date/time')
            return ''
        local_datetime = datetime.datetime.strptime(self.date_and_time, '%Y-%m-%dT%I:%M %p')
        return local_datetime.strftime('%Y-%m-%d %H:%M')

    def to_row(self) -> list:
        return [
            self.week,
            self.game_id,
            self.convert_to_local_date(),
            get_team_abbr(self.away_team_name),
            self.away_team_name,
            self.get_away_team_line(),
            get_team_abbr(self.home_team_name),
            self.home_team_name
        ]


class ScheduleParser(HTMLParser):

    def __init__(self, year: int, week: int):
        super().__init__()
        self.year: int = year
        self.week: int = week
        self.current_date: str = ''
        self.in_scoreboard_page = False
        self.node_stack: List[Node] = list()
        self.current_game: GameData = None
        self.games: List[GameData] = list()

    def run(self):
        input_file_name = self.get_input_file_name()
        if not os.path.isfile(input_file_name):
            raise FileNotFoundError(f'ERROR: File not found: {input_file_name}')
        with open(input_file_name, 'r') as f:
            super().feed(f.read())
        with open(self.get_output_file_name(), 'w') as f:
            header = ['week', 'game_id', 'date_and_time', 'away_team_abbr', 'away_team_name', 'away_team_line',
                      'home_team_abbr', 'home_team_name']
            writer = csv.writer(f)
            writer.writerow(header)
            self.games.sort(key=lambda x: x.date_and_time)
            for game_data in self.games:
                writer.writerow(game_data.to_row())

    def get_input_file_name(self) -> str:
        return f'{PROJECT_DIR}/html/nfl/{self.year}/week{self.week}.html'

    def get_output_file_name(self) -> str:
        return f'{PROJECT_DIR}/output/nfl/{self.year}/week{self.week}.csv'

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, '')

        # class ="Scoreboard__Row flex w-100 Scoreboard__Row__Main"
        # if tag == 'article' and node.has_class('scoreboard') and node.has_class('football'):
        if tag == 'header' and node.has_class('Card__Header'):
            date_str = node.get_attr('aria-label')
            if date_str != 'Bye Week Teams':
                self.current_date = datetime.datetime.strptime(date_str, '%A, %B %d, %Y').strftime('%Y-%m-%d')
        if tag == 'section' and node.has_class('Scoreboard'):
            # print(attrs)
            self.in_scoreboard_page = True
            self.current_game = GameData(self.week)
            self.games.append(self.current_game)
            game_id = node.get_attr('id')
            self.current_game.game_id = game_id
        if self.in_scoreboard_page:
            self.node_stack.append(node)

    def current_tag(self) -> str:
        return self.current_node().tag

    def current_node(self) -> Node:
        return self.node_stack[-1]

    def handle_endtag(self, tag):
        if self.in_scoreboard_page:
            self.node_stack.pop()
            if len(self.node_stack) == 0:
                self.in_scoreboard_page = False

    def handle_data(self, data):
        if not self.in_scoreboard_page:
            return
        self.current_node().data = data
        if self.current_tag() == 'div' and self.current_node().has_class('n9'):
            if data.strip().startswith('Line :'):
                self.current_game.line = data.replace('Line :', '').strip()
                print('line: ' + self.current_game.line)
        in_away_team_node = self.stack_contains('li', 'ScoreboardScoreCell__Item--away')
        in_home_team_node = self.stack_contains('li', 'ScoreboardScoreCell__Item--home')
        if self.current_tag() == 'div' and self.current_node().has_class('ScoreCell__TeamName'):
            # for some reason, away team node is still in the stack when it hits the home team node
            if in_away_team_node and not in_home_team_node:
                self.current_game.away_team_name = data
            elif in_home_team_node:
                self.current_game.home_team_name = data
        if self.current_tag() == 'div' and self.current_node().has_class('ScoreboardScoreCell__Time'):
            self.current_game.date_and_time = self.current_date + 'T' + data
        if self.current_tag() == 'span' and self.current_node().has_class('sb-team-abbrev'):
            if in_away_team_node:
                self.current_game.away_team_abbr = data
            elif in_home_team_node:
                self.current_game.home_team_abbr = data
        pass

    def stack_contains(self, tag: str, class_name: str) -> bool:
        for node in self.node_stack:
            if node.tag == tag and node.has_class(class_name):
                return True
        return False

    def error(self, message):
        pass


if __name__ == '__main__':
    # year_arg = sys.argv[1]
    year_arg = 2021
    # week_arg = sys.argv[2]
    week_arg = 8
    parser = ScheduleParser(int(year_arg), int(week_arg))
    parser.run()
