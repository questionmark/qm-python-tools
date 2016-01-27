#! /usr/bin/env python

import getpass
import json
import logging
import os.path
import ssl
import string
import StringIO
import sys
import time

from optparse import OptionParser

import pyslet.http.auth as auth
import pyslet.http.client as http
import pyslet.http.params as params
import pyslet.iso8601 as iso
import pyslet.odata2.client as client
import pyslet.odata2.core as odata
import pyslet.wsgi as wsgi
import pyslet.xml20081126.structures as xml

from pyslet.rfc2396 import URI
from pyslet.wsgi_django import DjangoApp

import aml


US_ONDEMAND = "https://ondemand.questionmark.com/deliveryodata/%s"
EU_ONDEMAND = "https://ondemand.questionmark.eu/deliveryodata/%s"

LETTERS="ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class DemoApp(DjangoApp):

    @classmethod
    def add_options(cls, parser):
        """Adds the following options:

        --cert              Path to certificate files for verification.

        -c, --customer_id   Set the customer id
        
        --deliveryodata     Set the deliveryodata URL (overrides -c)
        
        -u, --user          Set the service user name (defaults to customer_id)
        
        --password          Set the password (if not given, will prompt)"""
        super(DemoApp, cls).add_options(parser)
        parser.add_option(
            "--cert", dest="cert", default=None,
            help="Verify certificates using certificates in path")
        parser.add_option("-c", "--customerid", dest="customer_id",
                          help="Questionmark OnDemand customer id")
        parser.add_option("--deliveryodata", dest="deliveryodata_url",
                          help="Delivery OData URL (for Perception users)")
        parser.add_option("-u", "--user", dest="user",
                          help="user name for basic auth credentials")
        parser.add_option("--password", dest="password",
                          help="password for basic auth credentials")

    #: URL of the Delivery OData service 
    deliveryodata = None
    
    #: path to the certifcate file
    ca_path = None
    
    @classmethod
    def setup(cls, options=None, args=None, **kwargs):
        """Adds OData initialisation

        Loads the :attr:`metadata` document.  Creates the
        :attr:`data_source` according to the configured :attr:`settings`
        (creating the tables only if requested in the command line
        options).  Finally sets the :attr:`container` to the entity
        container for the application.

        If the -s or --sqlout option is given in options then the data
        source's create table script is output to standard output and
        sys.exit(0) is used to terminate the process."""
        super(DemoApp, cls).setup(options, args, **kwargs)
        settings = cls.settings.setdefault('DemoApp', {})
        customer_id = settings.setdefault('customer_id', None)
        url = settings.setdefault('deliveryodata', None)
        if url:
            # overrides customer_id in settings file
            customer_id = None
        if options and options.customer_id:
            # overrides url in settings file
            customer_id = options.customer_id
            url = None
        if options and options.deliveryodata_url:
            # overrides everything
            customer_id = None
            url = options.deliveryodata_url
        if customer_id:
            if customer_id.isdigit():
                if int(customer_id) < 600000:
                    url = US_ONDEMAND % customer_id
                else:
                    url = EU_ONDEMAND % customer_id
            elif customer_id.isalnum():
                url = US_ONDEMAND % customer_id
            else:
                sys.exit("Bad customer id: %s" % customer_id)
        if url:
            cls.deliveryodata = URI.from_octets(url)
            if not cls.deliveryodata.is_absolute():
                # resolve relative to the current working directory
                cls.deliveryodata = cls.deliveryodata.resolve(
                    URI.from_path(os.path.join(os.getcwd(), 'index')))
            elif not url.endswith('/'):
                url = url + '/'
        else:
            sys.exit("One of customer id or Delivery OData URL is required")
        if options and options.cert:
            # grab the certificate from the live server
            cls.ca_path = options.cert
        settings.setdefault('user', customer_id)
        if options and options.user is not None:
            settings['user'] = options.user
        settings.setdefault('password', None)
        if options and options.password is not None:
            settings['password'] = options.password
        if not settings['password']:
            settings['password'] = getpass.getpass()        

    def __init__(self, **kwargs):
        super(DemoApp, self).__init__(**kwargs)
        if self.ca_path is None:
            logging.warning("No certificate path set, SSL communication may "
                            "be vulnerable to MITM attacks")
        self.client = client.Client(ca_certs=self.ca_path, max_inactive=10)
        self.cookie_store = http.cookie.CookieStore()
        self.client.set_cookie_store(self.cookie_store)
        self.client.LoadService(self.deliveryodata)
        credentials = auth.BasicCredentials()
        credentials.userid = self.settings['DemoApp']['user']
        credentials.password = self.settings['DemoApp']['password']
        credentials.protectionSpace = \
            self.client.serviceRoot.GetCanonicalRoot()
        credentials.add_success_path(self.client.serviceRoot.abs_path)
        self.client.add_credentials(credentials)
        self.container = self.client.model.DataServices.defaultContainer
        
    def init_dispatcher(self):
        """Adds pre-defined pages for this application

        These pages are mapped to /ctest and /wlaunch.  These names are
        not currently configurable.  See :meth:`ctest` and
        :meth:`wlaunch` for more information."""
        super(DemoApp, self).init_dispatcher()
        self.set_method('/css/*', self.static_page)
        self.set_method('/images/*', self.static_page)
        self.set_method('/aicc', self.aicc)
        self.set_method('/aicc100', self.aicc100)
        # Pages for Printing and Scanning demonstration
        self.set_method('/pas', self.pas)
        self.set_method('/pasprepare', self.pas_prepare)
        self.set_method('/pasprint', self.pas_print)
        self.set_method('/pasprint2', self.pas_print2)
        self.set_method('/pasprint3', self.pas_print3)
        self.set_method('/pasprint4', self.pas_print4)
        self.set_method('/pasprint5', self.pas_print5)
        self.set_method('/pasprint6', self.pas_print6)
        self.set_method('/pasupload', self.pas_upload)
        self.set_method('/pasupload2', self.pas_upload2)
        self.set_method('/pasupload3', self.pas_upload3)
        self.set_method('/pasupload4', self.pas_upload4)
        self.set_method('/pasupload5', self.pas_upload5)
        self.set_method('/snapview', self.snapview)
        self.set_method('/snapviewxml', self.snapviewxml)
        self.set_method('/snapviewscan', self.snapviewscan)
        self.set_method('/snapshot', self.snapshot)
        # Pages for Online Proctoring System demonstration
        self.set_method('/ops', self.ops)
        self.set_method('/new_attempt', self.new_attempt_action)
        self.set_method('/launch', self.launch)
        self.set_method('/plaunch', self.plaunch)
        self.set_method('/*', self.home)

    def new_page_context(self, context):
        page_context = super(DemoApp, self).new_page_context(context)
        app_root = str(context.get_app_root())
        page_context['css_attr'] = xml.EscapeCharData7(
            app_root + 'css/base.css', True)
        page_context['favicon_attr'] = xml.EscapeCharData7(
            app_root + 'images/favicon.ico', True)
        page_context['home_attr'] = xml.EscapeCharData7(app_root, True)
        page_context['ops_attr'] = xml.EscapeCharData7(
            app_root + 'ops', True)
        page_context['pas_attr'] = xml.EscapeCharData7(
            app_root + 'pas', True)
        page_context['url'] = self.deliveryodata
        page_context['url_user'] = self.settings['DemoApp']['user']
        return page_context

    def home(self, context):
        page_context = self.new_page_context(context)
        with self.container['Assessments'].OpenCollection() as assessments:
            page_context['alist'] = assessments.values()
        with self.container['Attempts'].OpenCollection() as attempts:
            page_context['attempts'] = attempts.values()
        with self.container['Participants'].OpenCollection() as participants:
            page_context['participants'] = participants.values()
        data = self.render_template(context, 'home.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas(self, context):
        page_context = self.new_page_context(context)
        data = self.render_template(context, 'pas.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_prepare(self, context):
        page_context = self.new_page_context(context)
        with self.container['Assessments'].OpenCollection() as assessments:
            page_context['alist'] = assessments.values()
        with self.container['AssessmentSnapshots'].OpenCollection() as snapshots:
            page_context['snapshots'] = snapshots.values()
        with self.container['Participants'].OpenCollection() as participants:
            page_context['participants'] = participants.values()
        data = self.render_template(context, 'prepare.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_print(self, context):
        page_context = self.new_page_context(context)
        with self.container['Groups'].OpenCollection() as groups:
            page_context['groups'] = groups.values()
        with self.container['PrintBatches'].OpenCollection() as batches:
            blist = batches.values()
            for b in blist:
                b.CreatedDateTime_int = int(
                    b['CreatedDateTime'].value.with_zone(0).get_unixtime()
                    * 1000) - self.js_origin           
            page_context['batches'] = blist
        data = self.render_template(context, 'print.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_print2(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'POST':
            raise wsgi.MethodNotAllowed
        page_context = self.new_page_context(context)
        gid = context.get_form_long('gid')
        page_context['gid'] = gid
        with self.container['Assessments'].OpenCollection() as assessments:
            page_context['assessments'] = assessments.values()
        data = self.render_template(context, 'print2.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_print3(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'POST':
            raise wsgi.MethodNotAllowed
        page_context = self.new_page_context(context)
        gid = context.get_form_long('gid')
        aid = context.get_form_long('aid')
        page_context['gid'] = gid
        page_context['aid'] = aid
        # We don't have a navigation from Assessment to AssessmentSnaphot yet
        aid_value = odata.edm.EDMValue.NewSimpleValue(
            odata.edm.SimpleType.Int64)
        parser = odata.Parser("AssessmentID eq :aid")        
        filter = parser.parse_common_expression({'aid': aid_value})
        aid_value.set_from_value(aid)       
        with self.container[
                'AssessmentSnapshots'].OpenCollection() as snapshots:
            # and we don't support any useful filter either!
            # snapshots.set_filter(filter)
            results = []
            for s in snapshots.itervalues():
                if s['AssessmentID'].value == aid:
                    results.append(s)
            page_context['snapshots'] = results
        data = self.render_template(context, 'print3.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_print4(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'POST':
            raise wsgi.MethodNotAllowed
        page_context = self.new_page_context(context)
        gid = context.get_form_long('gid')
        aid = context.get_form_long('aid')
        sid = context.get_form_long('sid')
        page_context['gid'] = gid
        page_context['aid'] = aid
        page_context['sid'] = sid
        with self.container['Groups'].OpenCollection() as groups:
            g = groups[gid]
            with g['Participants'].OpenCollection() as participants:
                page_context['gcount'] = len(participants.keys())
        page_context['g'] = g
        with self.container['Assessments'].OpenCollection() as assessments:
            a = assessments[aid]
        page_context['a'] = a
        with self.container[
                'AssessmentSnapshots'].OpenCollection() as snapshots:
            s = snapshots[sid]
        page_context['s'] = s
        data = self.render_template(context, 'print4.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_print5(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'POST':
            raise wsgi.MethodNotAllowed
        page_context = self.new_page_context(context)
        gid = context.get_form_long('gid')
        aid = context.get_form_long('aid')
        sid = context.get_form_long('sid')
        bname = context.get_form_string('bname')
        with self.container['Groups'].OpenCollection() as groups:
            g = groups[gid]
            with g['Participants'].OpenCollection() as participants:
                page_context['gcount'] = len(participants.keys())
        page_context['g'] = g
        with self.container['Assessments'].OpenCollection() as assessments:
            a = assessments[aid]
        page_context['a'] = a
        with self.container[
                'AssessmentSnapshots'].OpenCollection() as snapshots:
            s = snapshots[sid]
        page_context['s'] = s
        with self.container['PrintBatches'].OpenCollection() as batches:
            b = batches.new_entity()
            b['ID'].set_from_value(0)
            b['Name'].set_from_value(bname)
            b['SnapshotID'].set_from_value(sid)
            b['GroupID'].set_from_value(gid)
            b['CreatedDateTime'].set_from_value(iso.TimePoint.from_now())            
            b['ModifiedDateTime'].set_from_value(b['CreatedDateTime'].value)            
            batches.insert_entity(b)
            page_context['b'] = b
            b.CreatedDateTime_int = int(
                b['CreatedDateTime'].value.with_zone(0).get_unixtime()
                * 1000) - self.js_origin
            page_context['created'] = True
        data = self.render_template(context, 'print5.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_print6(self, context):
        page_context = self.new_page_context(context)
        qparams = context.get_query()
        bid = long(qparams['bid'])
        with self.container['PrintBatches'].OpenCollection() as batches:
            batches.set_expand({"AssessmentSnapshot": None,
                                "Group": {"Participants": None}})
            b = batches[bid]
            b.CreatedDateTime_int = int(
                b['CreatedDateTime'].value.with_zone(0).get_unixtime()
                * 1000) - self.js_origin            
            page_context['b'] = b
            g = b['Group'].GetEntity()
            page_context['g'] = g
            with g['Participants'].OpenCollection() as participants:
                page_context['gcount'] = len(participants.keys())
            s = b['AssessmentSnapshot'].GetEntity()
            page_context['s'] = s
        # Now just the Assessment object to retrieve
        with self.container['Assessments'].OpenCollection() as assessments:
            a = assessments[s['AssessmentID'].value]
            page_context['a'] = a
        page_context['created'] = False
        data = self.render_template(context, 'print5.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_upload(self, context):
        page_context = self.new_page_context(context)
        with self.container['Groups'].OpenCollection() as groups:
            page_context['groups'] = groups.values()
        data = self.render_template(context, 'upload.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_upload2(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'POST':
            raise wsgi.MethodNotAllowed
        page_context = self.new_page_context(context)
        gid = context.get_form_long('gid')
        page_context['gid'] = gid
        with self.container['Groups'].OpenCollection() as groups:
            groups.set_expand({"PrintBatches": None})
            g = groups[gid]
            page_context['g'] = g
            with g['PrintBatches'].OpenCollection() as batches:
                page_context['blist'] = batches.values()
        data = self.render_template(context, 'upload2.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_upload3(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'GET':
            raise wsgi.MethodNotAllowed
        page_context = self.new_page_context(context)
        qparams = context.get_query()
        bid = long(qparams['bid'])
        with self.container['PrintBatches'].OpenCollection() as batches:
            batches.set_expand({"AssessmentSnapshot": None,
                                "Group": {"Participants": None}})
            b = batches[bid]
            b.CreatedDateTime_int = int(
                b['CreatedDateTime'].value.with_zone(0).get_unixtime()
                * 1000) - self.js_origin            
            page_context['b'] = b
            g = b['Group'].GetEntity()
            page_context['g'] = g
            with g['Participants'].OpenCollection() as participants:
                page_context['plist'] = participants.values()
            s = b['AssessmentSnapshot'].GetEntity()
            page_context['s'] = s
        # Now just the Assessment object to retrieve
        with self.container['Assessments'].OpenCollection() as assessments:
            a = assessments[s['AssessmentID'].value]
            page_context['a'] = a
        data = self.render_template(context, 'upload3.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_upload4(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'POST':
            raise wsgi.MethodNotAllowed
        page_context = self.new_page_context(context)
        bid = context.get_form_long('bid')
        pid = context.get_form_long('pid')
        with self.container['PrintBatches'].OpenCollection() as batches:
            batches.set_expand({"AssessmentSnapshot": None,
                                "Group": None})
            b = batches[bid]
            b.CreatedDateTime_int = int(
                b['CreatedDateTime'].value.with_zone(0).get_unixtime()
                * 1000) - self.js_origin            
            page_context['b'] = b
            g = b['Group'].GetEntity()
            page_context['g'] = g
            with g['Participants'].OpenCollection() as participants:
                page_context['p'] = participants[pid]
            s = b['AssessmentSnapshot'].GetEntity()
            sid = s['ID'].value
            page_context['s'] = s
        with self.container['Assessments'].OpenCollection() as assessments:
            a = assessments[s['AssessmentID'].value]
            page_context['a'] = a
        with self.container[
                'AssessmentSnapshotsData'].OpenCollection() as snapshots:
            out = StringIO.StringIO()
            snapshot_info = snapshots.read_stream(sid, out=out)
            out.seek(0)
            doc = aml.Document()
            doc.Read(src=out)
            qlist = []
            for b in doc.root.BlockSnapshot:
                if b.QuestionList:
                    for q in b.QuestionList.Question:
                        qlist.append(q)
                        q.aml_qnumber = len(qlist)
                        q.aml_choices = []
                        if q.Answer:
                            i = 0
                            for c in q.Answer.AnswerThing:
                                if isinstance(c, aml.Choice):
                                    q.aml_choices.append(LETTERS[i])
                                    i += 1
        page_context['qlist'] = qlist
        data = self.render_template(context, 'upload4.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def pas_upload5(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'POST':
            raise wsgi.MethodNotAllowed
        page_context = self.new_page_context(context)
        bid = context.get_form_long('bid')
        pid = context.get_form_long('pid')
        with self.container['PrintBatches'].OpenCollection() as batches:
            batches.set_expand({"AssessmentSnapshot": None,
                                "Group": None})
            b = batches[bid]
            b.CreatedDateTime_int = int(
                b['CreatedDateTime'].value.with_zone(0).get_unixtime()
                * 1000) - self.js_origin            
            page_context['b'] = b
            g = b['Group'].GetEntity()
            page_context['g'] = g
            with g['Participants'].OpenCollection() as participants:
                page_context['p'] = participants[pid]
            s = b['AssessmentSnapshot'].GetEntity()
            sid = s['ID'].value
            page_context['s'] = s
        with self.container['Assessments'].OpenCollection() as assessments:
            aid = s['AssessmentID'].value
            a = assessments[aid]
            page_context['a'] = a
        with self.container[
                'AssessmentSnapshotsData'].OpenCollection() as snapshots:
            out = StringIO.StringIO()
            snapshot_info = snapshots.read_stream(sid, out=out)
            out.seek(0)
            doc = aml.Document()
            doc.Read(src=out)
            answer_upload = {}
            qlist = []
            answer_upload["QuestionAndChoices"] = qlist
            for b in doc.root.BlockSnapshot:
                if b.QuestionList:
                    for q in b.QuestionList.Question:
                        qnum = len(qlist) + 1
                        clist = []
                        qentry = {"QuestionOrderNumber": qnum,
                                  "UploadedChoices": clist}
                        qlist.append(qentry)
                        response = context.get_form_string("q%i" % qnum)
                        if q.Answer:
                            i = 0
                            for c in q.Answer.AnswerThing:
                                if isinstance(c, aml.Choice):
                                    centry = {
                                        "ChoiceOrderNumber": unicode(i+1),
                                        "Selected": LETTERS[i] in response}
                                    clist.append(centry)
                                    i += 1
        with self.container['Attempts'].OpenCollection() as attempts:
            xid = "PAS:%i:%i" % (bid, pid)
            xid_value = odata.edm.EDMValue.NewSimpleValue(
                odata.edm.SimpleType.String)
            parser = odata.Parser("ExternalAttemptID eq :xid")        
            filter = parser.parse_common_expression({'xid': xid_value})
            xid_value.set_from_value(xid)       
            attempts.set_filter(filter)
            attempt = attempts.values()
            if attempt:
                attempt = attempt[0]
            else:
                attempt = attempts.new_entity()
                attempt['ID'].set_from_value(0)
                attempt['ExternalAttemptID'].set_from_value(xid)
                attempt['ParticipantID'].set_from_value(pid)
                attempt['AssessmentID'].set_from_value(aid)
                attempt['AssessmentSnapshotID'].set_from_value(sid)
                attempt['LockRequired'].set_from_value(True)
                attempt['LockStatus'].set_from_value(True)            
                attempt['LastModifiedDateTime'].set_from_value(iso.TimePoint.from_now())
                attempts.insert_entity(attempt)
            answer_upload['AttemptID'] = unicode(attempt['ID'].value)
        with self.container['AnswerUploads'].OpenCollection() as uploads:
            sinfo = odata.StreamInfo(
                type=params.MediaType.from_str('application/json'))
            sdata = StringIO.StringIO(
                json.dumps(answer_upload).encode("utf-8"))
            upload = uploads.new_stream(sdata, sinfo=sinfo)
            page_context['upload'] = upload
        page_context['answers'] = json.dumps(answer_upload)
        data = self.render_template(context, 'upload5.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def snapview(self, context):
        qparams = context.get_query()
        sid = long(qparams['sid'])
        with self.container['AssessmentSnapshots'].OpenCollection() as snapshots:
            snapshot = snapshots[sid]
        link = snapshot['PrintableDocumentSourceUrl'].value.split()
        rlink = string.join(link, '%20')
        if len(link) > 1:
            logging.error("URL contained unencoded space: %s" %
                          repr(snapshot['PrintableDocumentSourceUrl'].value))
        return self.redirect_page(
            context,
            URI.from_octets(rlink),
            303)

    def snapviewxml(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'GET':
            raise wsgi.MethodNotAllowed
        qparams = context.get_query()
        sid = long(qparams['sid'])
        try:
            snapshots = self.container[
                'AssessmentSnapshotsData'].OpenCollection()
            snapshot_info, sgen = snapshots.read_stream_close(sid)
            context.add_header("Content-Type", str(snapshot_info.type))
            if snapshot_info.size is not None:
                context.add_header("Content-Length", str(snapshot_info.size))
            context.set_status(200)
            context.start_response()
            snapshots = None
            return sgen
        finally:
            if snapshots is not None:
                snapshots.close()

    def snapviewscan(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'GET':
            raise wsgi.MethodNotAllowed
        qparams = context.get_query()
        sid = long(qparams['sid'])
        page_context = self.new_page_context(context)
        with self.container[
                'AssessmentSnapshotsData'].OpenCollection() as snapshots:
            out = StringIO.StringIO()
            snapshot_info = snapshots.read_stream(sid, out=out)
            out.seek(0)
            doc = aml.Document()
            doc.Read(src=out)
            qlist = []
            for b in doc.root.BlockSnapshot:
                if b.QuestionList:
                    for q in b.QuestionList.Question:
                        qlist.append(q)
                        q.aml_qnumber = len(qlist)
                        q.aml_choices = []
                        if q.Answer:
                            i = 0
                            for c in q.Answer.AnswerThing:
                                if isinstance(c, aml.Choice):
                                    q.aml_choices.append(LETTERS[i])
                                    i += 1
        page_context['qlist'] = qlist
        data = self.render_template(context, 'scansheet.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)            

    def snapshot(self, context):
        qparams = context.get_query()
        aid = long(qparams['aid'])
        with self.container['Assessments'].OpenCollection() as assessments:
            assessment = assessments[aid]
        with self.container['AssessmentSnapshots'].OpenCollection() as snapshots:
            s = snapshots.new_entity()
            s['ID'].set_from_value(0)
            s['AssessmentID'].set_from_value(aid)
            s['Name'].set_from_value(
                "DemoSnap/%s" % str(iso.TimePoint.from_now()))
            # <Property Name="PrintableDocumentSourceUrl" Type="Edm.String"/>
            # <Property Name="Language" Type="Edm.String"/>
            # <Property Name="CreatedDateTime" Type="Edm.DateTime" Nullable="false"/>
            # <Property Name="ModifiedDateTime" Type="Edm.DateTime" Nullable="false"/>
            # <Property Name="ExpiresDateTime" Type="Edm.DateTime"/>
            s['CreatedDateTime'].set_from_value(iso.TimePoint.from_now())
            s['ModifiedDateTime'].set_from_value(iso.TimePoint.from_now())
            snapshots.insert_entity(s)
        return self.redirect_page(
            context, URI.from_octets('pas').resolve(
                context.get_app_root()), 303)

    def aicc100(self, context):
        context.set_status(200)
        data = "error=0\r\n" \
"error_text=successful\r\n" \
"version=3.4\r\n" \
"aicc_data=[core]\r\n" \
"Student_ID=administrator\r\n" \
"Student_Name=Administrator,Kallidus\r\n" \
"Output_file=\r\n" \
"Credit=C\r\n" \
"Lesson_Location=\r\n" \
"Lesson_Mode=Sequential\r\n" \
"Lesson_Status=na,a\r\n" \
"Score=0\r\n" \
"Time=00:00:00\r\n" \
"[core_vendor]\r\n" \
"name=100\r\n" \
"[core_lesson]\r\n" \
"\r\n" \
"[Student_Data]\r\n" \
"Mastery_Score=0"
        return self.text_response(context, data)
    
    def aicc(self, context):
        context.set_status(200)
        data = "error=0\r\n" \
"error_text=successful\r\n" \
"version=3.4\r\n" \
"aicc_data=[core]\r\n" \
"Student_ID=administrator\r\n" \
"Student_Name=Administrator,Kallidus\r\n" \
"Output_file=\r\n" \
"Credit=C\r\n" \
"Lesson_Location=\r\n" \
"Lesson_Mode=Sequential\r\n" \
"Lesson_Status=na,a\r\n" \
"Score=0\r\n" \
"Time=00:00:00\r\n" \
"[core_vendor]\r\n" \
"100\r\n" \
"[core_lesson]\r\n" \
"\r\n" \
"[Student_Data]\r\n" \
"Mastery_Score=0"
        return self.text_response(context, data)

    def ops(self, context):
        page_context = self.new_page_context(context)
        with self.container['Assessments'].OpenCollection() as assessments:
            page_context['alist'] = assessments.values()
        with self.container['Attempts'].OpenCollection() as attempts:
            page_context['attempts'] = attempts.values()
        with self.container['Participants'].OpenCollection() as participants:
            page_context['participants'] = participants.values()
        data = self.render_template(context, 'ops.html', page_context)
        context.set_status(200)
        return self.html_response(context, data)

    def launch(self, context):
        qparams = context.get_query()
        aid = long(qparams['aid'])
        with self.container['Attempts'].OpenCollection() as attempts:
            attempt = attempts[aid]
        link = attempt['ParticipantFacingQMLobbyUrl'].value.split()
        rlink = string.join(link, '%20')
        if len(link) > 1:
            logging.error("URL contained unencoded space: %s" %
                          repr(attempt['ParticipantFacingQMLobbyUrl'].value))
#         if rlink.startswith('qmsb'):
#             # special handling of this redirect
#             page_context = self.new_page_context(context)
#             page_context['link_attr'] = xml.EscapeCharData7(str(rlink), True)
#             data = self.render_template(context, 'qmsb.html', page_context)
#             context.set_status(200)
#             return self.html_response(context, data)
#         else:
        return self.redirect_page(
            context,
            URI.from_octets(rlink),
            303)
        
    def plaunch(self, context):
        qparams = context.get_query()
        aid = long(qparams['aid'])
        with self.container['Attempts'].OpenCollection() as attempts:
            attempt = attempts[aid]
        link = attempt['ProctorFacingQMControlsWidgetUrl'].value.split()
        rlink = string.join(link, '%20')
        if len(link) > 1:
            logging.error(
                "URL contained unencoded space: %s" %
                repr(attempt['ProctorFacingQMControlsWidgetUrl'].value))
        return self.redirect_page(
            context,
            URI.from_octets(rlink),
            303)
        
    def new_attempt_action(self, context):
        if context.environ['REQUEST_METHOD'].upper() != 'POST':
            raise wsgi.MethodNotAllowed
        pid = context.get_form_long('pid')
        aid = context.get_form_long('aid')
        with self.container['Attempts'].OpenCollection() as attempts:
            a = attempts.new_entity()
            a['ID'].set_from_value(0)
            a['ExternalAttemptID'].set_from_value(
                "Heathrow/%s" % str(iso.TimePoint.from_now()))
            a['ParticipantID'].set_from_value(pid)
            a['AssessmentID'].set_from_value(aid)
            a['LockRequired'].set_from_value(True)
            a['LockStatus'].set_from_value(True)            
            a['ParticipantFacingProctorSystemWidgetUrl'].set_from_value("http://labs.adobe.com/technologies/cirrus/samples/")
            a['LastModifiedDateTime'].set_from_value(iso.TimePoint.from_now())
            attempts.insert_entity(a)
        return self.redirect_page(
            context, URI.from_octets('ops').resolve(
                context.get_app_root()), 303)
        

if __name__ == '__main__':
    parser = OptionParser()
    DemoApp.add_options(parser)
    (options, args) = parser.parse_args()
    DemoApp.settings_file = os.path.join(os.path.split(__file__)[0],
                                             'settings.json')
    DemoApp.setup(options, args)
    app = DemoApp()
    app.run_server()
