### AutoPkg for Ircam Forum software

Due to authentication requirements, it's necessary to find the required cookie keys before attempting to download Ircam Forum software. To do this follow the procedure below:

0. Using Google Chrome navigate to an Ircam software title, e.g. <http://forumnet.ircam.fr/shop/en/forumnet/10-audiosculpt.html>.
0. Click-on _Please log in_.
0. Enter your Ircam Forum credentials and click _Login_.
0. Open the Google Chrome _Developer Tools_, which are located under the View menu.
0. Go to the _Application_ tab in the tools and find _Cookies_ on the sidebar.
0. You need to copy two of the field:value pairs. These are:
  - The long alpha-numeric string field (first in the list).
  - The field beginning with "wordpress_logged_in_".
0. Enter these two pairs into the _AUTH_COOKIE_ input key in the recipe. Format is `field1=value1; field2=value2`, e.g:

```
<key>AUTH_COOKIE</key>
<string>asdhgajsgeqiu2y3i12y3iuyiuy34234=kfajh3i84skjdhfklareyahwefkhasfi7wehfhwfliewfhwhefisagfewgfliweahfhsaekfbjashflkuayblicrubywaeurycbiwaeyriuwa3yrkuwyrcuaywbl3kurcyawlkuryckwaly3crkwauycrlakwu3ycr; wordpress_logged_in_skfhaskfhsnrheurwln28742n2lic=blahblahblahblahblahetcetcetc</string>
```
