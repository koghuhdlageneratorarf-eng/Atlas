def say_hello():
    print('Hello')

def print_goodbye():
    print('Goodbye')

def test_error():
    try:
        # симулируем ошибку
        x = 1 / 0
    except ZeroDivisionError as e:
        print(f'Ошибка: {e}')

def main():
    say_hello()
    print_goodbye()
    test_error()

if __name__ == '__main__':
    main()