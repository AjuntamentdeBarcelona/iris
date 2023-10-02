import pytest

from profiles.actions.update_group_plates import UpdateGroupPlates
from profiles.models import Group
from profiles.tests.utils import create_groups


@pytest.mark.django_db
class TestUpdateGroupPlates:

    def test_update_group_descendants_plates(self):
        grand_parent, parent, first_soon, second_soon, noambit_parent, noambit_soon = create_groups()
        noambit_parent.parent = parent
        noambit_parent.save()
        Group.objects.rebuild()

        UpdateGroupPlates(noambit_parent).update_group_descendants_plates()

        grand_parent = Group.objects.get(pk=grand_parent.pk)
        parent = Group.objects.get(pk=parent.pk)
        first_soon = Group.objects.get(pk=first_soon.pk)
        second_soon = Group.objects.get(pk=second_soon.pk)
        noambit_parent = Group.objects.get(pk=noambit_parent.pk)
        noambit_soon = Group.objects.get(pk=noambit_soon.pk)

        assert grand_parent.calculate_group_plate() == f"{grand_parent.pk}-"
        assert parent.calculate_group_plate() == f"{grand_parent.pk}-{parent.pk}-"
        assert first_soon.calculate_group_plate() == f"{grand_parent.pk}-{parent.pk}-{first_soon.pk}-"
        assert second_soon.calculate_group_plate() == f"{grand_parent.pk}-{parent.pk}-{second_soon.pk}-"
        assert noambit_parent.calculate_group_plate() == f"{grand_parent.pk}-{parent.pk}-{noambit_parent.pk}-"
        assert noambit_soon.calculate_group_plate() == \
               f"{grand_parent.pk}-{parent.pk}-{noambit_parent.pk}-{noambit_soon.pk}-"
