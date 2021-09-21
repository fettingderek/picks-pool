#!/usr/bin/python3
import random

picks = {
    'DS': 4,
    'KenK': 6,
    'DF': 9,
    'RL': 9,
    'SD': 4,
    'KevK': 4,
    'JHan': 4,
    'JHor': 10,
    'MPit': 4,
    'JM': 4,
    'BVS': 10,
    'RH': 10,
    'EC': 2,
    'MK': 2,
    'BS': 2,
    'RP': 2,
    'JF': 4,
    'MPoy': 2,
    'BL': 3,
    'BH': 2,
    'JVA': 3
}


def main():
    # build the list
    squares = []
    for player, num_squares in picks.items():
        squares += [player for _ in range(0, num_squares)]

    # shuffle three times
    random.shuffle(squares)
    random.shuffle(squares)
    random.shuffle(squares)

    # write the squares array to a CSV
    with open('squares.csv', 'w') as f:
        for i, name in enumerate(squares):
            if i % 10 == 0:
                if i != 0:
                    f.write('\n')
            else:
                f.write(',')
            f.write(name)


if __name__ == '__main__':
    main()
