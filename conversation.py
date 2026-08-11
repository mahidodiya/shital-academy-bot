"""
conversation.py
Stores conversation context for the chatbot.
"""
class ConversationContext:

    def __init__(self):

        # Currently selected course
        self.current_course = None

    def set_course(self, course_id):

        self.current_course = course_id

    def get_course(self):

        return self.current_course

    def clear_course(self):

        self.current_course = None