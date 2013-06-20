# -*- coding: utf8 -*-
# SDAPS - Scripts for data acquisition with paper based surveys
# Copyright(C) 2008, Christoph Simon <post@christoph-simon.eu>
# Copyright(C) 2008, Benjamin Berg <benjamin@sipsolutions.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
u'''

Hinweis zu den Diamantstrukturen

Bei Klassen mit mehreren Basisklassen definiert maximal eine Basisklasse
eine eigene __init__ - Funktion. Die anderen Klassen sind "nur" Mixin - Klassen.
Dadurch werden die Probleme der Diamantstruktur umgangen.

'''

import buddy
import data
import struct


class DataObject(object):
    u'''Mixin
    '''

    def get_data(self):
        if not self.id in self.sheet.data:
            self.sheet.data[self.id] = getattr(data, self.__class__.__name__)(self)
        return self.sheet.data[self.id]

    data = property(get_data)


class Questionnaire(buddy.Object):
    '''
    Identification: There is only one.
    Reference: survey.questionnaire
    Parent: self.survey
    '''

    def __init__(self):
        self.survey = None
        self.qobjects = list()
        self.last_id = (0, 0)
        self.init_attributes()
        self._notify_changed_list = list()

    def init_attributes(self):
        self.page_count = 0

    def add_qobject(self, qobject, new_id=None):
        qobject.questionnaire = self
        # XXX: Is this any good?
        if new_id is not None:
            assert new_id > self.last_id
            self.last_id = new_id
            qobject.id = new_id
        else:
            self.last_id = qobject.init_id(self.last_id)
        self.qobjects.append(qobject)

    def get_sheet(self):
        return self.survey.sheet

    sheet = property(get_sheet)

    def notify_data_changed(self, qobj, dobj, name, old_value):
        for func in self._notify_changed_list:
            func(self, qobj, dobj, name, old_value)

    def connect_data_changed(self, func):
        self._notify_changed_list.append(func)

    def disconnect_data_changed(self, func):
        self._notify_changed_list.remove(func)

    def __unicode__(self):
        return unicode().join(
            [u'%s\n' % self.__class__.__name__] +
            [unicode(qobject) for qobject in self.qobjects]
        )

    def find_object(self, oid):
        for qobject in self.qobjects:
            obj = qobject.find_object(oid)

            if obj is not None:
                return obj

    def reinit_state(self):
        self._notify_changed_list = list()

class QObject(buddy.Object):
    '''
    Identification: id ==(major, minor)
    Reference: survey.questionnaire.qobjects[i](i != id)
    Parent: self.questionnaire
    '''

    def __init__(self):
        self.questionnaire = None
        self.boxes = list()
        self.last_id = -1
        self.init_attributes()

    def init_attributes(self):
        pass

    def init_id(self, id):
        self.id = (id[0], id[1] + 1)
        return self.id

    def add_box(self, box):
        box.question = self
        self.last_id = box.init_id(self.last_id)
        self.boxes.append(box)

    def get_sheet(self):
        return self.questionnaire.sheet

    sheet = property(get_sheet)

    def calculate_survey_id(self, md5):
        pass

    def id_str(self):
        ids = [str(x) for x in self.id]
        return u'.'.join(ids)

    def id_csv(self, theid=None):
        if theid is None:
            theid = self.id
        ids = [str(x) for x in theid]
        return u'_'.join(ids)

    def id_filter(self):
        ids = [str(x) for x in self.id]
        return u'_' + u'_'.join(ids)

    def __unicode__(self):
        return u'(%s)\n' % (
            self.__class__.__name__,
        )

    def find_object(self, oid):
        if self.id == oid:
            return self

        for box in self.boxes:
            obj = box.find_object(oid)

            if obj is not None:
                return obj

        return None


class Head(QObject):

    def init_attributes(self):
        QObject.init_attributes(self)
        self.title = unicode()

    def init_id(self, id):
        self.id = (id[0] + 1, 0)
        return self.id

    def __unicode__(self):
        return u'%s(%s) %s\n' % (
            self.id_str(),
            self.__class__.__name__,
            self.title,
        )


class Question(QObject):

    def init_attributes(self):
        QObject.init_attributes(self)
        self.page_number = 0
        self.question = unicode()

    def calculate_survey_id(self, md5):
        for box in self.boxes:
            box.calculate_survey_id(md5)

    def __unicode__(self):
        return u'%s(%s) %s {%i}\n' % (
            self.id_str(),
            self.__class__.__name__,
            self.question,
            self.page_number
        )


class Choice(Question):

    def __unicode__(self):
        return unicode().join(
            [Question.__unicode__(self)] +
            [unicode(box) for box in self.boxes]
        )

    def get_answer(self):
        '''it's a list containing all selected values
        '''
        answer = list()
        for box in self.boxes:
            if box.data.state:
                answer.append(box.value)
        return answer


class SingleChoice(Choice):
    
    def get_answer(self):
        '''it's the value of a single answer!
        returns -1 if no answer exists
        '''
        best_box = None
        for box in self.boxes[1:]:
            if box.data.state:
                if best_box is None:
                    best_box = box
                elif box.data.quality > best_box.data.quality:
                    best_box = box
        if best_box is None:
            return -1
        else:
            return best_box.value


class Mark(Question):

    def init_attributes(self):
        Question.init_attributes(self)
        self.answers = list()

    def __unicode__(self):
        if len(self.answers) == 2:
            return unicode().join(
                [Question.__unicode__(self)] +
                [u'\t%s - %s\n' % tuple(self.answers)] +
                [unicode(box) for box in self.boxes]
            )
        else:
            return unicode().join(
                [Question.__unicode__(self)] +
                [u'\t? - ?\n'] +
                [unicode(box) for box in self.boxes]
            )

    def get_answer(self):
        '''it's an integer between 0 and 5
        1 till 5 are valid marks, 0 is returned if there's something wrong
        '''
        # box.value is zero based, a mark is based 1
        answer = list()
        for box in self.boxes:
            if box.data.state:
                answer.append(box.value)
        if len(answer) == 1:
            return answer[0] + 1
        else:
            return 0

    def set_answer(self, answer):
        for box in self.boxes:
            box.data.state = box.value == answer - 1


class Text(Question):

    def __unicode__(self):
        return unicode().join(
            [Question.__unicode__(self)] +
            [unicode(box) for box in self.boxes]
        )

    def get_answer(self):
        '''it's a bool, wether there is content in the textbox
        '''
        assert len(self.boxes) == 1
        return self.boxes[0].data.state


class Additional_Head(Head):

    pass


class Additional_Mark(Question, DataObject):

    def init_attributes(self):
        Question.init_attributes(self)
        self.answers = list()

    def __unicode__(self):
        return unicode().join(
            [Question.__unicode__(self)] +
            [u'\t%s - %s\n' % tuple(self.answers)]
        )

    def get_answer(self):
        return self.data.value

    def set_answer(self, answer):
        self.data.value = answer


class Additional_FilterHistogram(Question, DataObject):

    def init_attributes(self):
        Question.init_attributes(self)
        self.answers = list()
        self.filters = list()

    def __unicode__(self):
        result = []
        result.append(Question.__unicode__(self))
        for i in xrange(len(self.answers)):
            result.append(u'\t%s - %s\n' % (self.answers[i], self.filters[i]))
        return unicode().join(result)

    def get_answer(self):
        return self.data.value

    def set_answer(self, answer):
        raise NotImplemented()


class Box(buddy.Object, DataObject):
    '''
    Identification: id of the parent and value of the box ::

        id == (major, minor, value)

    Reference: survey.questionnaire.qobjects[i].boxes[j]
    Parent: self.question
    '''

    def __init__(self):
        self.question = None
        self.init_attributes()

    def init_attributes(self):
        self.page_number = 0
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.text = unicode()

    def init_id(self, id):
        self.value = id + 1
        self.id = self.question.id + (self.value,)
        return self.value

    def id_str(self):
        ids = [str(x) for x in self.id]
        return u'.'.join(ids)

    def get_sheet(self):
        return self.question.sheet

    sheet = property(get_sheet)

    def calculate_survey_id(self, md5):
        tmp = struct.pack('!ffff', self.x, self.y, self.width, self.height)
        md5.update(tmp)

    def __unicode__(self):
        return u'\t%i(%s) %s %s %s %s %s\n' % (
            self.value,
            (self.__class__.__name__).ljust(8),
            (u'%.1f' % self.x).rjust(5),
            (u'%.1f' % self.y).rjust(5),
            (u'%.1f' % self.width).rjust(5),
            (u'%.1f' % self.height).rjust(5),
            self.text
        )

    def find_object(self, oid):
        if self.id == oid:
            return self


class Checkbox(Box):

    def init_attributes(self):
        Box.init_attributes(self)
        self.form = "box"

    def calculate_survey_id(self, md5):
        Box.calculate_survey_id(self, md5)
        md5.update(self.form)

class Textbox(Box):

    pass

