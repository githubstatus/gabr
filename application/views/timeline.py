from __future__ import absolute_import

import functools
import urllib

import flask

from application import utils
from application.models import twitter
from application.utils import decorators


def timeline(title, api_func):
    data = {
        "title": title,
        "results": list(),
    }
    try:
        results = api_func().json()
    except twitter.Error as e:
        flask.flash("Error: %s" % str(e))
    else:
        data["results"] = results
    return data


@decorators.login_required
@decorators.templated("timeline.html")
def home_timeline():
    params = flask.request.args.to_dict()
    params["include_entities"] = 1
    params["model_version"] = 7
    params["tweet_mode"] = "extended"
    data = timeline("Home", functools.partial(flask.g.api.get, "statuses/home_timeline", params=params))
    data["results"] = utils.remove_status_by_id(data["results"], params.get("max_id"))
    data["next_page_url"] = utils.build_next_page_url(data["results"], flask.request.args.to_dict())
    return data


@decorators.login_required
@decorators.templated("timeline.html")
def notifications_timeline():
    params = flask.request.args.to_dict()
    params["include_entities"] = 1
    params["include_my_retweet"] = 1
    params["include_rts"] = 1
    params["model_version"] = 7
    params["tweet_mode"] = "extended"
    data = timeline("Notifications", functools.partial(flask.g.api.get, "activity/about_me", version="1.1", params=params))
    data["results"] = utils.remove_status_by_id(data["results"], params.get("max_id"))
    data["next_page_url"] = utils.build_next_page_url(data["results"], flask.request.args.to_dict(),
                                                      key_name="max_position")
    return data


@decorators.login_required
@decorators.templated("timeline.html")
def search_tweets():
    params = flask.request.args.to_dict()
    params["q"] = urllib.unquote(params["q"]).encode("utf8")
    params["include_entities"] = 1
    params["model_version"] = 7
    params["tweet_mode"] = "extended"
    data = timeline("Search", functools.partial(flask.g.api.get, "search/tweets", params=params))
    data["results"] = utils.remove_status_by_id(data["results"]["statuses"], params.get("max_id"))
    data["next_page_url"] = utils.build_next_page_url(data["results"], params)
    return data


@decorators.login_required
@decorators.templated("timeline.html")
def user_favorites(screen_name):
    params = flask.request.args.to_dict()
    params["include_entities"] = 1
    params["model_version"] = 7
    params["tweet_mode"] = "extended"
    data = timeline("%s Favorites" % screen_name, functools.partial(flask.g.api.get, "favorites/list",
                                                                    screen_name=screen_name, params=params))
    data["results"] = utils.remove_status_by_id(data["results"], params.get("max_id"))
    data["next_page_url"] = utils.build_next_page_url(data["results"], flask.request.args.to_dict())
    return data
