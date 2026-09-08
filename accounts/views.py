from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import LoginView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, ListView, UpdateView, View

from accounts.forms import FlatLoginForm, InviteFlatmateForm, MemberProfileForm
from accounts.models import User
from accounts.services import build_invite_link, create_flatmate


@method_decorator(login_not_required, name="dispatch")
class FlatLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = FlatLoginForm
    redirect_authenticated_user = True


@method_decorator(login_not_required, name="dispatch")
class SetPasswordView(PasswordResetConfirmView):
    """The far end of an invite link.

    ``post_reset_login`` drops the new flatmate straight into the app instead
    of bouncing them to a login form they would have to fill in immediately.
    """

    template_name = "accounts/set_password.html"
    post_reset_login = True
    success_url = reverse_lazy("core:dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Password set. Welcome to the flat.")
        return super().form_valid(form)


class StaffOnlyMixin(UserPassesTestMixin):
    """Member administration is the flat admin's job, not everyone's."""

    def test_func(self) -> bool:
        return self.request.user.is_staff


class MemberListView(ListView):
    model = User
    template_name = "accounts/members.html"
    context_object_name = "members"

    def get_queryset(self):
        return User.objects.all().order_by("-is_active_member", "id")


class InviteFlatmateView(StaffOnlyMixin, FormView):
    template_name = "accounts/invite.html"
    form_class = InviteFlatmateForm

    def form_valid(self, form):
        user = create_flatmate(**form.cleaned_data)
        return self.render_to_response(
            self.get_context_data(
                form=self.form_class(),
                created_user=user,
                invite_link=build_invite_link(user, self.request),
            )
        )


class MemberUpdateView(StaffOnlyMixin, UpdateView):
    model = User
    form_class = MemberProfileForm
    template_name = "accounts/member_form.html"
    success_url = reverse_lazy("accounts:members")

    def form_valid(self, form):
        messages.success(self.request, f"Saved {form.instance.name}.")
        return super().form_valid(form)


class ProfileView(UpdateView):
    """Anyone editing their own details -- notably their UPI ID."""

    model = User
    form_class = MemberProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None) -> User:
        return self.request.user

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Tenancy dates are an admin decision, not self-service.
        for field in ("joined_on", "left_on"):
            form.fields.pop(field, None)
        return form

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


class AwayPeriodListView(ListView):
    template_name = "accounts/away_list.html"
    context_object_name = "periods"

    def get_queryset(self):
        from accounts.models import AwayPeriod

        return AwayPeriod.objects.select_related("user")

    def get_context_data(self, **kwargs):
        from accounts.forms import AwayPeriodForm

        context = super().get_context_data(**kwargs)
        context["form"] = AwayPeriodForm(actor=self.request.user)
        context["mine"] = [p for p in context["periods"] if p.user_id == self.request.user.pk]
        return context


class AwayPeriodCreateView(FormView):
    template_name = "accounts/away_list.html"
    success_url = reverse_lazy("accounts:away")

    def get_form_class(self):
        from accounts.forms import AwayPeriodForm

        return AwayPeriodForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["actor"] = self.request.user
        return kwargs

    def form_valid(self, form):
        period = form.save()
        messages.success(
            self.request,
            f"Marked {period.user.name} away for {period.days} day"
            f"{'s' if period.days != 1 else ''}.",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        from accounts.models import AwayPeriod

        return self.render_to_response(
            self.get_context_data(
                form=form, periods=AwayPeriod.objects.select_related("user")
            )
        )


class AwayPeriodDeleteView(View):
    def post(self, request, pk):
        from accounts.models import AwayPeriod

        period = get_object_or_404(AwayPeriod, pk=pk)
        if period.user_id != request.user.pk and not request.user.is_staff:
            raise PermissionDenied("You can only remove your own away days.")
        period.delete()
        messages.success(request, "Removed.")
        return redirect("accounts:away")
