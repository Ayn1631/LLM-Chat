<template>
  <div>
    <!-- 聊天窗口内容 -->
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import type { Chat } from '../App.vue';

export default defineComponent({
  name: 'ChatWindow',
  emits: ['send-message'],
  props: {
    currentChat: {
      type: Object as () => Chat,
      required: true,
      default: () => ({
        id: 'default',
        title: '新对话',
        messages: []
      })
    }
  },
  setup(props, { emit }) {
    const sendMessage = (message) => {
      emit('send-message', message);
    };

    return {
      sendMessage
    };
  }
});
</script>

<style scoped>
/* 聊天窗口样式 */
</style>