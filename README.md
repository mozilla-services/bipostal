BIPostal
==

BrowserID plugin for Postfix/Sendmail Milter system
--

***Note: This is very much beta***

See <a href="https://wiki.mozilla.org/Services/Notifications/Bipostal">the Mozilla Wiki page</a> for more info

### What does this do?

BIPostal provides a set of Sendmail Plugin filters that provide pseudonymous email addresses for use with BrowserID.

### Say again?

BrowserID is neat. It lets you log into a site with an email address that 
some other site vouches really belongs to you. The problem is that 
sometimes you may not want that other site to have your email address. 

Bipostal is designed to give you an email address that you can send to those
sites. It forwards to your real email address. The other site might know who
you are, but you can control if you want to hear from them or just drop them
altogether. 

### What's it need?

This package requires the following packages:

* Python 2.6

* PostFix (or any other milter compatible MTA)

* <a href="https://github.com/jrconlin/ppymilter2">ppymilter2</a>

    Slightly tweaked to use gevent instead of async core

* <a href="https://github.com/jrconlin/bipostal_store">bipostal_store</a>

    Common storage library for bipostal. (You'll need to configure this.)

* <a href="https://github.com/jrconlin/bipostal_dash">bipostal_dash</a>

    An API/Dashboard for bipostal. Handy if you want to, you know, use it.

### How do I use it?

Once you've got it set up, you can use bipostal\_dash to create new aliases.
It's not yet wired into BrowserID, but I hope it will be soon.

### I have more questions!

See <a href="https://wiki.mozilla.org/Services/Notifications/Bipostal">the Mozilla Wiki page</a> for more info
