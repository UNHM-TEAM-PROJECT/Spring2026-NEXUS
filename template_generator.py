"""
Template Generator module
This module generates a syllabus template based on the missing
information from the user's input file.
Reads the template, replaces the placeholders with the provided information,
and returns the completed template
"""


def generate_template(preferred_contact_method):

    with open("syllabus_template.txt", "r") as f:
        template = f.read()

    filled_template = template.replace(
        "{{preferred_contact_method}}",
        preferred_contact_method
    )

    return filled_template
