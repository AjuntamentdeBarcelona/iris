from model_mommy import mommy
from profiles.models import Group, GroupReassignation


def create_groups(create_reasignations=True, create_dair_reassignation=False):
    tree_id = 1
    grand_parent = mommy.make(Group, user_id="11111", profile_ctrl_user_id="11111", description="11111",
                              is_ambit=True, tree_id=tree_id, level=0, lft=1, rght=12, group_plate="1-")

    parent = mommy.make(Group, user_id="22222", profile_ctrl_user_id="22222", description="22222",
                        parent=grand_parent, is_ambit=True, tree_id=tree_id, level=1, lft=2, rght=7, group_plate="1-2-")
    first_soon = mommy.make(Group, user_id="33333", profile_ctrl_user_id="33333", description="33333",
                            parent=parent, is_ambit=True, tree_id=tree_id, level=2, lft=3, rght=4, group_plate="1-2-3-")
    second_soon = mommy.make(Group, user_id="44444", profile_ctrl_user_id="44444", description="44444",
                             parent=parent, is_ambit=False, tree_id=tree_id, level=2, lft=5, rght=6,
                             group_plate="1-2-4-")
    noambit_parent = mommy.make(Group, user_id="55555", profile_ctrl_user_id="55555", description="55555",
                                parent=grand_parent, is_ambit=False, tree_id=tree_id, level=1, lft=8, rght=11,
                                group_plate="1-5-")
    noambit_soon = mommy.make(Group, user_id="66666", profile_ctrl_user_id="66666", description="66666",
                              parent=noambit_parent, is_ambit=False, tree_id=tree_id, level=2, lft=9, rght=10,
                              group_plate="1-5-6-")

    if create_reasignations:
        GroupReassignation.objects.create(origin_group=parent, reasign_group=first_soon)
        GroupReassignation.objects.create(origin_group=parent, reasign_group=second_soon)
        GroupReassignation.objects.create(origin_group=parent, reasign_group=noambit_parent)

        if create_dair_reassignation:
            GroupReassignation.objects.create(origin_group=grand_parent, reasign_group=parent)
            GroupReassignation.objects.create(origin_group=grand_parent, reasign_group=noambit_parent)

    return grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon


def add_extra_group_level(parent_group):
    group = mommy.make(Group, user_id="group", profile_ctrl_user_id="group", description="group",
                       parent=parent_group, is_ambit=True, tree_id=parent_group.tree_id, level=parent_group.level +1,
                       lft=3, rght=4)
    group.group_plate = group.calculate_group_plate()
    group.save()


def create_notification_group(notifications_emails="", records_next_expire=False, records_next_expire_freq=1,
                              records_next_expire_notif_date=None, records_allocation=False, pend_records=False,
                              pend_records_freq=1, pend_records_notif_date=None, pend_communication=False,
                              pend_communication_freq=1):
    return mommy.make(Group, user_id='222222', profile_ctrl_user_id='2222222',
                      notifications_emails=notifications_emails, records_next_expire=records_next_expire,
                      records_next_expire_freq=records_next_expire_freq,
                      records_next_expire_notif_date=records_next_expire_notif_date,
                      records_allocation=records_allocation, pend_records=pend_records,
                      pend_records_freq=pend_records_freq, pend_records_notif_date=pend_records_notif_date,
                      pend_communication=pend_communication, pend_communication_freq=pend_communication_freq)


def dict_groups(create_reasignations=True, create_dair_reassignation=False):
    return {gr.pk: gr for gr in create_groups(create_reasignations=create_reasignations,
                                              create_dair_reassignation=create_dair_reassignation)}
