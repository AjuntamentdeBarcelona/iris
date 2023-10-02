from celery.schedules import crontab


def scheduled_tasks():
    return {
        "send_mail": {
            "task": "main.tasks.send_mail",
            "schedule": 30.0,
            "show_log": False,
        },
        "retry_deferred": {
            "task": "main.tasks.retry_deferred",
            "schedule": crontab(minute="47"),
            "show_log": False,
        },
        "check_messages_response_time_expired": {
            "task": "communications.tasks.check_messages_response_time_expired",
            "schedule": crontab(minute="*/15"),
            "show_log": False,
        },
        "delete_chuncked_files": {
            "task": "record_cards.tasks.delete_chuncked_files",
            "schedule": crontab(minute="*/14"),
            "show_log": False,
        },
        "delete_support_chuncked_files": {
            "task": "support_info.tasks.delete_support_chuncked_files",
            "schedule": crontab(minute="*/16"),
            "show_log": False,
        },
        "check_failed_group_delete_registers": {
            "task": "profiles.tasks.check_failed_group_delete_registers",
            "schedule": crontab(hour="0", minute="13")
        },
        "check_failed_elementdetail_delete_registers": {
            "task": "themes.tasks.check_failed_elementdetail_delete_registers",
            "schedule": crontab(hour="1", minute="13")
        },
        "send_next_to_expire_notifications": {
            "task": "profiles.tasks.send_next_to_expire_notifications",
            "schedule": crontab(hour="2", minute="17")
        },
        "send_pending_validate_notifications": {
            "task": "profiles.tasks.send_pending_validate_notifications",
            "schedule": crontab(hour="2", minute="28")
        },
        "send_records_pending_communications_notifications": {
            "task": "profiles.tasks.send_records_pending_communications_notifications",
            "schedule": crontab(hour="2", minute="39")
        },
        "generate_open_data_report": {
            "task": "integrations.tasks.generate_open_data_report",
            "schedule": crontab(month_of_year="*/3", day_of_month="3", hour="19", minute="0")
        },
        "generate_mib_report_literals": {
            "task": "integrations.tasks.generate_mib_report_literals",
            "schedule": crontab(hour="18", minute="0"),
            "user_retry": True,
        },
        "calculate_last_month_indicators": {
            "task": "record_cards.tasks.calculate_last_month_indicators",
            "schedule": crontab(day_of_month="1", hour="3", minute="33")
        },
        "themes_average_close_days": {
            "task": "themes.tasks.themes_average_close_days",
            "schedule": crontab(hour="3", minute="38")
        },
        "remove_celery_results": {
            "task": "integrations.manual_task_schedule.remove_celery_results",
            "schedule": crontab(hour="2", minute="0"),
            "show_log": False,
        }
    }
