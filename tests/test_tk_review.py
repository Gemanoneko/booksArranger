"""Exercise the actual Tk review controller without constructing a native window."""
import types
import unittest
from unittest.mock import patch

import app

class Variable:
    def __init__(self,value=None):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value

class Widget:
    created=[]
    def __init__(self,*args,**kwargs):
        self.kwargs=kwargs;self.position={};self.destroyed=False
        self.created.append(self)
    def title(self,*args):pass
    def transient(self,*args):pass
    def pack(self,**kwargs):pass
    def grid(self,**kwargs):self.position=kwargs
    def configure(self,**kwargs):self.kwargs.update(kwargs)
    def destroy(self):self.destroyed=True

class TkReviewTests(unittest.TestCase):
    def dialog(self,kind='audiobook'):
        Widget.created=[]
        captures=[]
        row={'kind':kind,'root':'fixture-root','path':'fixture-source','size':10,'modified':123,
             'review':{'original_language':'Other','title':'Book','author':'King Stephen','canonical_author':'Stephen King','narrator':'Reader Name','multi_author':True,'anthology':False}}
        instance=app.App.__new__(app.App)
        instance.window=Widget()
        instance.inventory=types.SimpleNamespace(save_review=lambda *args:captures.append(args))
        instance.selected_row=lambda:row
        instance.refresh=lambda:None
        instance.selected=lambda:None
        fake_tk=types.SimpleNamespace(Toplevel=Widget,StringVar=Variable,BooleanVar=Variable)
        fake_ttk=types.SimpleNamespace(**{name:Widget for name in ['Frame','Label','Entry','Combobox','Checkbutton','Button']})
        with patch.object(app,'tk',fake_tk),patch.object(app,'ttk',fake_ttk):
            instance.review()
        return captures

    def input_after_label(self,text):
        label=next(widget for widget in Widget.created if widget.kwargs.get('text')==text)
        return next(widget for widget in Widget.created if widget.position.get('row')==label.position['row'] and widget.position.get('column')==1 and 'textvariable' in widget.kwargs)

    def test_native_review_retains_routes_and_persists_separate_roles(self):
        captures=self.dialog()
        folder=self.input_after_label('Author folder name (Surname Firstname)')
        canonical=self.input_after_label('Author for Artist tag')
        narrator=self.input_after_label('Reader / narrator (for comments)')
        anthology=next(widget for widget in Widget.created if widget.kwargs.get('text')=='Short-story collection by multiple authors')
        multi=next(widget for widget in Widget.created if widget.kwargs.get('text','').startswith('Series has multiple authors'))
        anthology.kwargs['variable'].set(True);anthology.kwargs['command']()
        self.assertEqual(folder.kwargs['state'],'disabled')
        self.assertEqual(multi.kwargs['state'],'disabled')
        self.assertEqual(folder.kwargs['textvariable'].get(),'King Stephen')
        self.assertTrue(multi.kwargs['variable'].get())
        anthology.kwargs['variable'].set(False);anthology.kwargs['command']()
        self.assertEqual(folder.kwargs['state'],'normal')
        self.assertEqual(multi.kwargs['state'],'normal')
        anthology.kwargs['variable'].set(True);anthology.kwargs['command']()
        save=next(widget for widget in Widget.created if widget.kwargs.get('text')=='Save preview metadata')
        self.assertGreater(save.position['row'],multi.position['row'])
        self.assertGreater(save.position['row'],narrator.position['row'])
        save.kwargs['command']()
        review=captures[0][2]
        self.assertTrue(review['anthology'])
        self.assertTrue(review['multi_author'])
        self.assertEqual(review['author'],'King Stephen')
        self.assertEqual(review['canonical_author'],canonical.kwargs['textvariable'].get())
        self.assertEqual(review['narrator'],'Reader Name')

    def test_ebook_native_review_has_no_audiobook_controls(self):
        self.dialog('ebook')
        labels={widget.kwargs.get('text') for widget in Widget.created}
        self.assertNotIn('Short-story collection by multiple authors',labels)
        self.assertNotIn('Author for Artist tag',labels)
        self.assertNotIn('Reader / narrator (for comments)',labels)

if __name__=='__main__':unittest.main()
