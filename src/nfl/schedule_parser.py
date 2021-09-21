import csv
import os
import sys
from typing import List

import datetime
from dateutil import tz

import requests
from dataclasses import dataclass
from html.parser import HTMLParser

PROJECT_DIR = '/Users/derek/PycharmProjects/squarespool'


@dataclass
class Node:
    tag: str
    attrs: list
    data: str

    def has_class(self, class_name: str) -> bool:
        result = class_name == self.get_attr('class')
        return result

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
        line_parts = self.line.split(' ')
        if line_parts[0] == self.away_team_abbr:
            return line_parts[1]
        return -1 * float(line_parts[1])

    def convert_to_local_date(self):
        utc_datetime = datetime.datetime.strptime(self.date_and_time, '%Y-%m-%dT%H:%MZ')
        utc_datetime = utc_datetime.replace(tzinfo=tz.tzutc())
        local_datetime = utc_datetime.astimezone(tz.tzlocal())
        return local_datetime.strftime('%Y-%m-%d %H:%M')

    def to_row(self) -> list:
        return [
            self.week,
            self.game_id,
            self.convert_to_local_date(),
            self.away_team_abbr,
            self.away_team_name,
            self.get_away_team_line(),
            self.home_team_abbr,
            self.home_team_name
        ]


class ScheduleParser(HTMLParser):

    def __init__(self, year: int, week: int):
        super().__init__()
        self.year: int = year
        self.week: int = week
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

    def fetch_schedule_html(self):
        url = f'https://www.espn.com/nfl/scoreboard/_/year/{self.year}/seasontype/2/week/{self.week}'
        resp = requests.get(url)
        with open(self.get_input_file_name(), 'w') as f:
            f.write(resp.text)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, '')
        if tag == 'div' and node.has_class('scoreboard-wrapper'):
            self.in_scoreboard_page = True
            self.current_game = GameData(self.week)
            self.games.append(self.current_game)
        if self.in_scoreboard_page:
            self.node_stack.append(node)
            if tag == 'th' and node.has_class('date-time'):
                self.current_game.date_and_time = node.get_attr('data-date')
            if self.stack_contains('section', 'sb-actions') and tag == 'a' and 'gamecast' in node.get_attr('name'):
                link = node.get_attr('href')
                game_id = link.split('/')[-1]
                self.current_game.game_id = game_id

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
        if self.current_tag() == 'th' and self.current_node().has_class('line'):
            self.current_game.line = data
        in_away_team_node = self.stack_contains('td', 'away')
        in_home_team_node = self.stack_contains('td', 'home')
        if self.current_tag() == 'span' and self.current_node().has_class('sb-team-short'):
            if in_away_team_node:
                self.current_game.away_team_name = data
            elif in_home_team_node:
                self.current_game.home_team_name = data
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
    year_arg = sys.argv[1]
    week_arg = sys.argv[2]
    parser = ScheduleParser(int(year_arg), int(week_arg))
    parser.run()
