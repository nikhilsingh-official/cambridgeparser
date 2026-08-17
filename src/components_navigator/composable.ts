import { ref } from "vue";

const showOverview = ref(false);
const showTools = ref(false);

export function getShowStates() {
    return { showOverview, showTools }
}