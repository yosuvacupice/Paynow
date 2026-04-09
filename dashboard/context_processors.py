from django.utils import timezone

from core.models import UserAccount

from .models import MoneyRequest


def header_notifications(request):
    user_email = request.session.get('user_email')
    notifications = []

    if not user_email:
        return {'header_notifications': notifications, 'header_notification_count': 0}

    user = UserAccount.objects.filter(email=user_email).first()
    if not user:
        return {'header_notifications': notifications, 'header_notification_count': 0}

    requests = MoneyRequest.objects.filter(
        recipient_user=user,
        status=MoneyRequest.STATUS_PENDING,
    ).select_related('requester_bank__user')[:3]

    for money_request in requests:
        notifications.append({
            'id': money_request.id,
            'requester_name': money_request.requester_bank.account_holder_name or money_request.requester_bank.user.name,
            'requester_upi_id': money_request.requester_bank.upi_id,
            'amount': money_request.amount,
            'note': money_request.note,
            'time_label': _get_notification_time_label(money_request.created_at),
        })

    return {
        'header_notifications': notifications,
        'header_notification_count': len(notifications),
    }


def _get_notification_time_label(created_at):
    local_time = timezone.localtime(created_at)
    today = timezone.localdate()
    request_date = local_time.date()

    if request_date == today:
        return "Today"
    if (today - request_date).days == 1:
        return "Yesterday"
    return request_date.strftime('%d %b %Y')
