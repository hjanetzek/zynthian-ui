from zyngui import zynthian_widget_drawbar
from zyngui import zynthian_widget_data as wd

class zynthian_widget_setbfree(zynthian_widget_drawbar.zynthian_widget_drawbar):


    def __init__(self, parent):
        super().__init__(parent)
        self.drawbars = wd.drawbar_symbols(None, setbfree=True)

