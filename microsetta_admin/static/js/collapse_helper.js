//See https://stackoverflow.com/questions/18992839/hide-show-content-if-some-option-is-selected-with-bootstrap

// This function assumes existence of several classes tagging the select item
// and the collapsible fields.
// * All collapsible fields must be marked with the bootstrap "collapse" tag
// * Fields dependent on selection value should be marked with "collapse_XXX"
//   where XXX is the select_id
// * Fields dependent on selection value must also have "collapse_YYY"
//   where YYY is the is the option value for which they should be shown
// * Finally, fields dependent on choosing anything other than the start value
//   should have the class "collapse_XXX_changed" where XXX is the select_id
//
// Would recommend also disabling collapse transitions for this use case by
// adding something like
// https://stackoverflow.com/questions/13119912/disable-bootstraps-collapse-open-close-animation
// .collapse_XXX {
//    transition: none !important;
// }
// where XXX is the select_id to the css

function register_select_collapse(select_id, start_value) {
    $('#' + select_id).change(function()
    {
        var value = $(this).val();
        var to_hide = '.collapse_' + select_id;
        var to_show = '.collapse_' + value;
        var not_default = '.collapse_' + select_id + '_changed';

        $(to_hide).collapse('hide');
        if (value !== start_value) {
            $(to_show).collapse('show');
            $(not_default).collapse('show');
        }
        else {
            $(not_default).collapse('hide');
        }
    }
);


}