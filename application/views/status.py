from __future__ import absolute_import

import operator

import flask

from application.libs import render
from application.models import twitter
from application.utils import decorators


@decorators.login_required
def status_post():
    data = dict()
    if flask.request.method == "POST":
        status_text = flask.request.form.get("status")
        if status_text:
            media_file = flask.request.files.get("media[]")
            try:
                retweet_id = flask.request.form.get("retweet_id")
                if "retweet" in flask.request.form and retweet_id:
                    result = flask.g.api.post("statuses/retweet/%s" % retweet_id, {"tweet_mode": "extended", }).json()
                else:
                    in_reply_to_id = flask.request.form.get("in_reply_to_id")
                    kwargs = {
                        "status": status_text,
                        "tweet_mode": "extended",
                    }
                    if in_reply_to_id:
                        kwargs["in_reply_to_status_id"] = in_reply_to_id
                    if media_file:
                        endpoint = "statuses/update_with_media"
                        kwargs["files"] = {
                            "media[]": media_file,
                        }
                    else:
                        endpoint = "statuses/update"
                    result = flask.g.api.post(endpoint, **kwargs).json()
            except twitter.Error as e:
                flask.flash("Post error: %s" % str(e))
                data["preset_status"] = status_text
            else:
                result["current"] = True
                data["title"] = "Tweet %s" % result["id_str"]
                data["results"] = [result]
                return flask.render_template("results.html", **data)
    data["title"] = "What's happening?"
    return flask.render_template("status_post.html", **data)


@decorators.login_required
@decorators.templated("results.html")
def status(status_id):
    data = {
        "title": "Status %s" % status_id,
    }

    tweets = []
    try:
        tweets = flask.g.api.get("conversation/show", {"id": status_id, "count": 20, "tweet_mode": "extended", }).json()
    except twitter.Error as e:
        flask.flash("Get conversation error: %s" % str(e))

    contain_status = False
    fetched_ids = set()
    for tweet in tweets:
        fetched_ids.add(tweet["id"])
        if tweet["id_str"] == status_id:
            tweet["current"] = True
            contain_status = True

    if not contain_status:
        try:
            tweet = flask.g.api.get("statuses/show/%s" % status_id, {"tweet_mode": "extended", }).json()
        except twitter.Error as e:
            flask.flash("Get status error: %s" % str(e))
        else:
            tweet["current"] = True
            tweets.append(tweet)

    # If a tweet has its parent not added, add it.
    for i, status in enumerate(tweets):
        if "retweeted_status" not in status:
            current_id = status["in_reply_to_status_id"]
        else:
            current_id = status["retweeted_status"]["in_reply_to_status_id"]
        if current_id and current_id not in fetched_ids:
            fetched_ids.add(current_id)
            try:
                status = flask.g.api.get("statuses/show/%s" % current_id, {"tweet_mode": "extended", }).json()
            except twitter.Error:
                pass
            else:
                tweets.append(status)

    tweets.sort(key=operator.itemgetter("id"))

    # If too few tweets and the first tweet still has its parent, add them until enough.
    while 0 < len(tweets) <= 4:
        status = tweets[0]
        if status['in_reply_to_status_id_str']:
            current_id = status['in_reply_to_status_id']
            if current_id in fetched_ids:
                break
            try:
                status = flask.g.api.get("statuses/show/%d" % current_id, {"tweet_mode": "extended", }).json()
            except twitter.Error:
                break
        else:
            break
        if 'retweeted_status' in status and status["retweeted_status"]["id"] not in fetched_ids:
            tweets.insert(0, status['retweeted_status'])
            fetched_ids.add(status['retweeted_status']["id"])
        elif status["id"] not in fetched_ids:
            tweets.insert(0, status)
            fetched_ids.add(status["id"])

    data["results"] = tweets
    return data


@decorators.login_required
@decorators.templated("status_post.html")
def status_reply(status_id):
    data = {
        "title": "Reply to %s" % status_id,
    }
    try:
        result = flask.g.api.get("statuses/show/%s" % status_id, {"tweet_mode": "extended", }).json()
    except twitter.Error as e:
        flask.flash("Get status error: %s" % str(e))
    else:
        data["preset_status"] = "@%s " % result["user"]["screen_name"]
        data["in_reply_to_id"] = status_id
        data["in_reply_to_status"] = render.prerender_tweet(result)
    return data


@decorators.login_required
@decorators.templated("status_post.html")
def status_replyall(status_id):
    data = {
        "title": "Reply to All %s" % status_id,
    }
    try:
        result = flask.g.api.get("statuses/show/%s" % status_id, {"tweet_mode": "extended", }).json()
    except twitter.Error as e:
        flask.flash("Get status error: %s" % str(e))
    else:
        data["in_reply_to_status"] = render.prerender_tweet(result)
        mentioned_screen_name = [result["user"]["screen_name"]]
        entities = result.get("entities")
        if entities:
            for user_mention in entities.get("user_mentions", list()):
                if user_mention["screen_name"] not in mentioned_screen_name:
                    mentioned_screen_name.append(user_mention["screen_name"])
        if flask.g.screen_name in mentioned_screen_name and len(mentioned_screen_name) > 1:
            mentioned_screen_name.remove(flask.g.screen_name)
        data["preset_status"] = "%s " % " ".join("@%s" % x for x in mentioned_screen_name)
    return data


@decorators.login_required
@decorators.templated("status_post.html")
def status_retweet(status_id):
    data = {
        "title": "Retweet %s" % status_id,
    }
    try:
        result = flask.g.api.get("statuses/show/%s" % status_id, {"tweet_mode": "extended", }).json()
    except twitter.Error as e:
        flask.flash("Get status error: %s" % str(e))
    else:
        data["retweet_status"] = result
        if result["user"]["protected"]:
            preset_status = " RT @%s: %s" % (result["user"]["screen_name"], result["full_text"])
        else:
            preset_status = " https://twitter.com/%s/status/%s" % (result["user"]["screen_name"], status_id)
        data["preset_status"] = preset_status
    return data


@decorators.login_required
@decorators.templated("results.html")
def status_favorite(status_id):
    data = {
        "title": "Favorite %s" % status_id,
    }
    try:
        result = flask.g.api.post("favorites/create", {"id": status_id, "tweet_mode": "extended", }).json()
    except twitter.Error as e:
        flask.flash("Create favorite error: %s" % str(e))
    else:
        flask.flash("Created favorite successfully!")
        result["favorited"] = True  # fucking twitter won't mark it as favorited.
        result["current"] = True
        data["results"] = [result]
    return data


@decorators.login_required
@decorators.templated("results.html")
def status_unfavorite(status_id):
    data = {
        "title": "Unfavorite %s" % status_id,
    }
    try:
        result = flask.g.api.post("favorites/destroy", {"id": status_id, "tweet_mode": "extended", }).json()
    except twitter.Error as e:
        flask.flash("Destroy favorite error: %s" % str(e))
    else:
        flask.flash("Destroyed favorite successfully!")
        result["favorited"] = False  # fucking twitter won't mark it as not favorited.
        result["current"] = True
        data["results"] = [result]
    return data


@decorators.login_required
def status_delete(status_id):
    data = {
        "title": "Delete %s" % status_id,
    }
    if flask.request.method == "GET":
        data["status_id"] = status_id
        return flask.render_template("status_delete.html", **data)
    try:
        result = flask.g.api.post("statuses/destroy/%s" % status_id, {"tweet_mode": "extended", }).json()
    except twitter.Error as e:
        flask.flash("Destroy status error: %s" % str(e))
    else:
        flask.flash("Destroyed status successfully!")
        result["deleted"] = True
        result["current"] = True
        data["results"] = [result]
    return flask.render_template("results.html", **data)
