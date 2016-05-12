import sys
import re
from workflow import Workflow, web

GREEN_ICON = True
INCLUDE_DISABLED = False

class Jenkins:

    def main(self, workflow):
        self.workflow = workflow

        #self.configure()

        query = self.get_query()

        self.query_jobs(query)

    def configure(self):
        # TODO:
        # Need a way to configure this:
        self.workflow.settings['jenkins_url'] = 'https://jenkins/'
        self.workflow.settings['jenkins_username'] = 'username'
        # self.workflow.save_password('jenkins_password', '<password>')


    def query_jobs(self, query):
        json = self.get_cached_jobs_json()

        jobs = json['jobs'] if json else []
        jobs = self.apply_filters(jobs)

        if self.is_regex_query(query):
            regex_query = self.get_regex_query(query)
            jobs = filter(lambda job: re.match(regex_query, job['name']), jobs)
            if not jobs:
                self.workflow.add_item('Regular expression "%s" matches no jobs' % regex_query,
                    subtitle='Hint: Queries starting with a slash "/" are considered to be regular expressions.')
        elif query:
            jobs = self.workflow.filter(query, jobs, lambda job: job['name'])

        for job in jobs:
            self.workflow.add_item(job['name'],
                                   subtitle=job['url'],
                                   arg=job['url'],
                                   valid=True,
                                   autocomplete=job['name'],
                                   icon=self.icon_path(job['color']))

        self.workflow.send_feedback()

    def is_regex_query(self, query):
        return bool(self.get_regex_query(query))

    def get_regex_query(self, query):
        match = re.match("^/(.*?)/?$", query)
        if match:
            return match.group(1)
        return None

    def get_jobs_json(self):
        url = self.workflow.settings['jenkins_url'] + '/api/json?tree=jobs[name,url,color,lastBuild[url]]'
        auth = (self.workflow.settings['jenkins_username'], self.workflow.get_password('jenkins_password'))
        response = web.get(url=url, auth=auth)
        response.raise_for_status()
        return response.json()

    def get_cached_jobs_json(self):
        return self.workflow.cached_data('jenkins_jobs', self.get_jobs_json, max_age=10)

    def get_query(self):
        if self.workflow.args:
            words = self.workflow.args[0].split(' ')
            query_words = []
            for word in words:
                if word[:3] != 'is:':
                    query_words.append(word)
            return ' '.join(query_words)
        return None

    def apply_filters(self, jobs):
        result = jobs
        if self.workflow.args:
            words = self.workflow.args[0].strip().split(' ')
            filters = []
            possible_filters = [('is:stable', 'blue', lambda job: job['color'] in ['blue', 'blue_anime']),
                                ('is:unstable', 'yellow', lambda job: job['color'] in ['yellow', 'yellow_anime']),
                                ('is:failing', 'red', lambda job: job['color'] in ['red', 'red_anime']),
                                ('is:aborted', 'gray', lambda job: job['color'] == 'aborted'),
                                ('is:enabled', 'blue', lambda job: job['color'] != 'disabled'),
                                ('is:disabled', 'gray', lambda job: job['color'] == 'disabled'),]
            for i in range(len(words)):
                word = words[i]
                if word[:3] != 'is:':
                    continue
                filter_found = False
                for possible_filter in possible_filters:
                    if word == possible_filter[0]:
                        filter_found = True
                        result = filter(possible_filter[2], result)
                if not filter_found:
                    filtered_filters = self.workflow.filter(word, possible_filters, lambda possible_filter: possible_filter[0])
                    previous_words = words[0:-1]
                    auto_complete_prefix = ' '.join(previous_words) + ' ' if previous_words else ''
                    for filtered_filter in filtered_filters:
                        self.workflow.add_item(filtered_filter[0],
                                          autocomplete=auto_complete_prefix + filtered_filter[0],
                                          icon=self.icon_path(filtered_filter[1]))

                        result = []
                return result
        return filter(lambda job: INCLUDE_DISABLED or job['color'] != 'disabled', result)

    def icon_path(self, job_color):
        icon = job_color.replace('_anime', '')
        if GREEN_ICON and icon == 'blue':
            icon = 'green'
        elif not icon in ['blue', 'red', 'yellow']:
            icon = 'grey'

        return 'icons/' + icon + '.png'


if __name__ == u'__main__':
    sys.exit(Workflow().run(Jenkins().main))
