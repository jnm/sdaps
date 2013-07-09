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

import os

from sdaps import model
from sdaps import script

from sdaps.utils.ugettext import ugettext, ungettext
_ = ugettext


parser = script.subparsers.add_parser("find_global_id",
    help=_("Write something."),
    description=_("""Write something else.
    """))

# maybe later
#parser.add_argument('--pickle',
#    help=_("Output a pickled tuple of (file name, page number, global id)."),
#    action="pickle_output",
#    default=False)

parser.add_argument('images',
    help=_("A number of TIFF image files."),
    nargs='+')

@script.connect(parser)
@script.logfile
def add(cmdline):
    from sdaps import surface
    from sdaps import matrix
    from sdaps.recognize import buddies
    from sdaps import image
    from sdaps.utils.exceptions import RecognitionError
    import subprocess
    import sys
    import shutil
    class Expando: pass

    survey = model.survey.Survey()
    survey.defs.style = "code128"
    survey.defs.paper_width = 210.0
    survey.defs.paper_height = 297.0
    survey.survey_dir = '.'

    for file in cmdline['images']:

        print _('Processing %s') % file

        if not image.check_tiff_monochrome(file):
            print _('Invalid input file %s. You need to specify a (multipage) monochrome TIFF as input.') % (file,)
            #raise AssertionError()
            continue # just skip the file

        num_pages = image.get_tiff_page_count(file)

        tiff = file
        tiff = os.path.relpath(os.path.abspath(tiff), survey.survey_dir)

        pages = range(num_pages)
        while len(pages) > 0:
            img = model.sheet.Image()
            img.filename = tiff
            img.tiff_page = pages.pop(0)
            img.sheet = Expando()
            img.sheet.survey = survey
            img.surface.load()
            try:
                if img.rotated:
                    img.surface.load()
                    img.recognize.calculate_matrix()
                img.recognize.calculate_global_id()
            except RecognitionError:
                pass # let img.global_id remain None
            # repr() a tuple, maybe we'll eval() it *gasp* somewhere else
            # print an * at the beginning to distinguish from SDAPS noise
            print '*', repr((img.filename, img.tiff_page, img.global_id))

        print _('Done')
