#!/usr/bin/env python3

import requests
import sys


# Code based on the following: https://stackoverflow.com/questions/42002336/using-python-requests-module-to-login-on-an-wordpress-based-website
def main():
    auth_url = "https://forumnet.ircam.fr:3443//login"
    desired_url = ""

    s = requests.Session()

    login_data = {"username": "username", "password": "password",
                  "rememberme": "forever"
                  # "redirect_to": "http://forumnet.ircam.fr/",
                  # "redirect_to_automatic": "1"
                  }




    page_login = s.post(auth_url, data=login_data)

    # modalys_page = s.get('http://forumnet.ircam.fr/product/modalys-en/')
    # audiosculpt_page = s.get('http://forumnet.ircam.fr/shop/en/forumnet/10-audiosculpt.html')

    # print(s.cookies)
    # print(audiosculpt_page.cookies.get_dict())

    # audiosculpt_down = s.get("http://forumnet.ircam.fr/shop/en/get-file.php?id=1735")
    #
    # print(audiosculpt_down.text.encode('utf-8'))

    print(page_login.text)

    s.close()

    sys.exit(0)


if __name__ == '__main__':
    main()
