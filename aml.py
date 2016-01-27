#! /usr/bin/env python
"""This module implements the AssessmentSnapshot markup specification
defined by Questionmark."""

import itertools

import pyslet.xml20081126.structures as xml
import pyslet.xsdatatypes20041028 as xsi
import pyslet.qml420 as qml


class Element(xml.Element):
    """Basic element to represent all AML-defined elements"""
    pass


class BooleanElement(Element):
    """Base class for elements with boolean values.

    Boolean values are represented by the string "true" or "false"."""
    XMLCONTENT = xml.ElementType.Mixed

    def is_true(self):
        return self.GetValue().strip().lower() == "true"
        
    def is_false(self):
        return self.GetValue().strip().lower() == "false"

        
class AssessmentId(Element):
    """The ID of the Assessment"""
    XMLNAME = 'AssessmentId'
    XMLCONTENT = xml.ElementType.Mixed


class Header(Element):
    """The snapshot header"""
    XMLNAME = 'Header'
    XMLCONTENT = xml.ElementType.ElementContent


class BlockSnapshotId(Element):
    """The ID of this block snapshot"""
    XMLNAME = 'BlockSnapshotId'
    XMLCONTENT = xml.ElementType.Mixed


class BlockType(Element):
    """The ID of this block snapshot"""
    XMLNAME = 'BlockType'
    XMLCONTENT = xml.ElementType.Mixed


class BlockId(Element):
    """The ID of the block that has been snapshotted"""
    XMLNAME = 'BlockId'
    XMLCONTENT = xml.ElementType.Mixed


class BlockName(Element):
    """The name of the block"""
    XMLNAME = 'BlockName'
    XMLCONTENT = xml.ElementType.Mixed


class BlockNumber(Element):
    """The number of the block, starting at 1"""
    XMLNAME = 'BlockNumber'
    XMLCONTENT = xml.ElementType.Mixed


class ShowFeedback(BooleanElement):
    """Whether feedback is shown
    
    The element's value will be either "true" or "false".  Note the
    unconventional spelling of FeedBack in the element name."""
    XMLNAME = 'ShowFeedBack'
    XMLCONTENT = xml.ElementType.Mixed


class ShuffleQuestions(BooleanElement):
    """Whether questions were shuffled
    
    The element's value will be either "true" or "false"."""
    XMLNAME = 'ShuffleQuestions'
    XMLCONTENT = xml.ElementType.Mixed


class IntroductionText(Element):
    """The Block's introductory text."""
    XMLNAME = 'introductionText'
    XMLCONTENT = xml.ElementType.Mixed


class AnswerThing(Element):
    """Base class for anything that can be inside ANSWER"""
    pass


class Answer(Element):
    """Represents the Answer element."""
    XMLNAME = 'ANSWER'
    XMLCONTENT = xml.ElementContent
    XMLATTR_QTYPE = ('qType', qml.ParseNameString, qml.FormatNameString)
    XMLATTR_COMMENT = ('comment', qml.ParseYesNoEnum, qml.FormatYesNoEnum)
    XMLATTR_SUBTYPE = ('subType', qml.ParseDirectionEnum, qml.FormatDirectionEnum)

    def __init__(self, parent):
        Element.__init__(self, parent)
        self.qType = None
        self.comment = None
        self.subType = None
        self.AnswerThing = []

    def GetChildren(self):
        for child in self.AnswerThing:
            yield child


class Choice(AnswerThing):
    """Represents a choice."""
    XMLNAME = 'CHOICE'
    XMLCONTENT = xml.ElementContent
    XMLATTR_QML_ID = ('qid', qml.ParseNameString, qml.FormatNameString)
    XMLATTR_ID = ('cid', xsi.DecodeInteger, xsi.EncodeInteger)

    def __init__(self, parent):
        AnswerThing.__init__(self, parent)
        self.qid = None
        self.cid = None
        self.Content = None

    def GetChildren(self):
        if self.Content:
            yield self.Content


class Question(Element):
    """QML-like QUESTION element"""
    XMLNAME = 'QUESTION'
    XMLATTR_ID = ('qid', xsi.DecodeInteger, xsi.EncodeInteger)
    XMLATTR_Min = ('min', xsi.DecodeInteger, xsi.EncodeInteger)
    XMLATTR_MAX = ('max', xsi.DecodeInteger, xsi.EncodeInteger)
    XMLATTR_TOPIC = 'topic'
    XMLATTR_TOPICDESCRIPTION = 'topic_description'
    XMLATTR_Type = ('type', qml.ParseNameString, qml.FormatNameString)
    XMLATTR_Revision = ('revision', xsi.DecodeInteger, xsi.EncodeInteger)
    XMLATTR_Block = ('block', xsi.DecodeInteger, xsi.EncodeInteger)
    XMLATTR_QuestionID = ('question_id', xsi.DecodeInteger, xsi.EncodeInteger)
    XMLATTR_Description = 'description'
    XMLCONTENT = xml.ElementContent

    def __init__(self, parent):
        Element.__init__(self, parent)
        self.qid = None
        self.min = None
        self.max = None
        self.topic = None
        self.topic_description = None
        self.type = None
        self.revision = None
        self.block = None
        self.question_id = None
        self.description = 'Question Description'
        self.Content = []
        self.Outcomes = []
        self.Answer = None
        
    def GetChildren(self):
        for child in itertools.chain(
                self.Content,
                self.Outcomes):
            yield child
        if self.Answer:
            yield self.Answer


class QuestionList(Element):
    """The list of questions within the block."""
    XMLNAME = 'questionList'
    XMLCONTENT = xml.ElementType.ElementContent

    def __init__(self, parent):
        Element.__init__(self, parent)
        self.Question = []

    def GetChildren(self):
        for child in self.Question:
            yield child


class BlockSnapshot(Element):
    """Represents a single block in the snapshot"""
    XMLNAME = 'BlockSnapshot'
    XMLCONTENT = xml.ElementType.ElementContent

    def __init__(self, parent):
        Element.__init__(self, parent)
        self.BlockSnapshotId = BlockSnapshotId(self)
        self.BlockType = BlockType(self)
        self.BlockId = BlockId(self)
        self.BlockName = BlockName(self)
        self.BlockNumber = BlockNumber(self)
        self.ShowFeedback = ShowFeedback(self)
        self.ShuffleQuestions = ShuffleQuestions(self)
        self.IntroductionText = None
        self.QuestionList = None
        
    def GetChildren(self):
        yield self.BlockSnapshotId
        yield self.BlockType
        yield self.BlockId
        yield self.BlockName
        yield self.BlockNumber
        yield self.ShowFeedback
        yield self.ShuffleQuestions
        if self.IntroductionText:
            yield self.IntroductionText
        if self.QuestionList:
            yield self.QuestionList
    
    
class AssessmentSnapshot(Element):
    """AssessmentSnapshot root element."""
    XMLNAME = 'AssessmentSnapshot'
    XMLCONTENT = xml.ElementType.ElementContent
    
    def __init__(self, parent):
        Element.__init__(self, parent)
        self.AssessmentId = AssessmentId(self)
        self.Header = Header(self)
        self.BlockSnapshot = []
    
    def GetChildren(self):
        yield self.AssessmentId
        yield self.Header
        for child in self.BlockSnapshot:
            yield child


class Document(xml.Document):
    """Class for working with AssessmentSnapshot documents."""

    def __init__(self, **args):
        """"""
        xml.Document.__init__(self, **args)

    classMap = {}
    """classMap is a mapping from element names to the class object that will be
	used to represent them."""

    def get_element_class(self, name):
        """Returns the class to use to represent an element with the given name.

        This method is used by the XML parser.  The class object is looked up in
        :py:attr:`classMap`, if no specialized class is found then the general
        :py:class:`pyslet.xml20081126.Element` class is returned."""
        return Document.classMap.get(
            name, Document.classMap.get(None, xml.Element))


xml.MapClassElements(Document.classMap, globals())
