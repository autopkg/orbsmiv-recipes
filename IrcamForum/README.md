### AutoPkg for Ircam Forum software

Combine URLDownloader and URLTextSearcher, getting an auth cookie and then using it to search and then to download (if necessary).

#### Curl code

To get cookie from login page:
```
curl -L -b cookie.txt -c cookie.txt -d "username=username&password=password&rememberme=forever" https://forumnet.ircam.fr:3443//login
```

To use cookie:
```
curl -L -b cookie.txt http://forumnet.ircam.fr/shop/en/forumnet/10-audiosculpt.html
```

The cookie will need to be stored in a temp location and then removed.
