
class Good():
    def eval(self, hello):
        print 'eval in Good', hello

    def exe(self, hello):
        print 'exec in Good', hello


eval("hehehehe")
exec("hahahaha")
Good().eval("hehehe")
Good().exe("hahaha")
