#!/opt/pyenv/versions/2.7.18/bin/python
# -*- coding: utf-8 -*-
import urllib
import urllib2
import json
import argparse
import syslog

class AjaxAPI(object):

    def __init__(self, url, **args):
        self.api_url = url
        self.username = 'azkaban' if not args.has_key('username') else args['username']
        self.password = 'azkaban' if not args.has_key('password') else args['password']
        self.session_id = None

    def auth(self):
        session_id = None
        headers = {}
        params = {'action':'login', 'username':self.username, 'password':self.password}
        http_req = urllib2.Request(self.api_url, urllib.urlencode(params), headers)
        http_res = urllib2.urlopen(http_req)
        api_res = json.loads(http_res.read())
        if api_res['status'] == 'success':
            self.session_id = api_res['session.id']
            return api_res
        else:
            raise Exception("Authentication failed.")

    def execute_flow(self, **args):
        project     = args['project']
        flow        = args['flow']
        params      = None if not args.has_key('params') else args['params']
        # concurrentOption (Possible Values: skip, pipline)
        #  Concurrent choices. Use skip if nothing specifical is required.
        concurrent  = 'skip' if not args.has_key('concurrent') else args['concurrent']

        execute_params = {
                'session.id':self.session_id, 'ajax':'executeFlow',
                'project':project, 'flow':flow,
                'concurrentOption': concurrent}

        if 'pipeline' in concurrent:
            pipeline_level = 1 if not args.has_key('pipeline_level') else args['pipeline_level']
            execute_params['pipelineLevel'] = pipeline_level # pipeline:1, pipline:2

        # {'telnet.password': 'casa', 'telnet.username': 'root', 'telnet.host': 'x.x.x.x'}
        if params:
            for k, v in params.iteritems():
                execute_params['flowOverride[' + k + ']'] = v

        http_res = urllib.urlopen(self.api_url + '?' + urllib.urlencode(execute_params))
        api_res = json.loads(http_res.read())

        if api_res.has_key('error'):
            raise Exception(api_res['error'])
        else:
            return api_res

def cli():
    # parse options
    parser = argparse.ArgumentParser(description='CLI for AakabanAPI')
    parser.add_argument('-a', '--azkaban', action="store", dest="host", help="azkaban host", default="localhost")
    parser.add_argument('-p', '--port', action="store", dest="port", help="azkaban port", default=8081)
    parser.add_argument('-username', '--username', action="store", dest="username", help="azkaban username", default="azkaban")
    parser.add_argument('-password', '--password', action="store", dest="password", help="azkaban password", default="azkaban")
    parser.add_argument('-project', '--project', action="store", dest="project", help="azkaban project", default=None)
    parser.add_argument('-flow', '--flow', action="store", dest="flow", help="azkaban flow", default=None)
    parser.add_argument('-k', '--key', action="append", dest="key", help="azkaban flow override key")
    parser.add_argument('-v', '--value', action="append", dest="value", help="azkaban flow override value")
    parser.add_argument('-e', '--execute', action="store_true", dest="execute_flow", help="execute flow")
    parser.add_argument('-concurrent', '--concurrent', action="store", dest="concurrent", help="", default="skip")
    parser.add_argument('-level', '--pipelinelevel', action="store", dest="level", help="", default="1")
    args = parser.parse_args()

    params = None
    if args.key and args.value:
        params = {k:v for k, v in zip(args.key, args.value)}

    syslog.syslog("project: %s, flow: %s, params: %s" % (args.project, args.flow, str(params)))

    if args.execute_flow:
        url = "http://" + args.host + ":" + str(args.port) + '/executor'
        api = AjaxAPI(url, username=args.username, password=args.password)
        res = api.auth()
        status = res['status']
        syslog.syslog("authentication: %s" % status)
        if status == 'success':
            syslog.syslog('starting flow...')
            try:
                res = api.execute_flow(
                        project=args.project, flow=args.flow,
                        params=params,
                        concurrent=args.concurrent,
                        pipeline_level=args.level)
                syslog.syslog(res['message'])
            except Exception as e:
                syslog.syslog(syslog.LOG_ERR, "Exception caught: %s" % e.message)
        else:
           syslog.syslog(syslog.LOG_ERR, 'Exception caught: authentication error.')

if __name__ == "__main__":
    cli()
