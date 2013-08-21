class WizardMixin(object):
    wizard = False
    
    def get_context_data(self, **kwargs):
        context = super(WizardMixin, self).get_context_data(**kwargs)
        if self.wizard:
            context["base_template"] = 'wizard.html'
            context["wizard_mode"] = True
        else:
            context["base_template"] = 'base.html'
            context["wizard_mode"] = False
        return context
