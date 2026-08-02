def say_goodbye():
        # say_hello() - функция не определена, поэтому вызовем ее с проверкой
        if 'say_hello' in globals():
            say_hello()
        else:
            print("say_hello не определена")
