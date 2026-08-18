<template>
  <span
    class="key-star"
    :class="{ 'is-key': active }"
    role="button"
    tabindex="0"
    :title="title"
    @click="$emit('toggle')"
  >
    <svg class="ks-svg" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
    </svg>
  </span>
</template>

<script setup>
defineProps({
  active: { type: Boolean, default: false },
  title: { type: String, default: '点击 ★/☆ 切换重点客户' }
})
defineEmits(['toggle'])
</script>

<style scoped>
.key-star {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f0f2f5;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}
.key-star:hover {
  transform: scale(1.1);
  background: #fff7e6;
}
.key-star:active {
  transform: scale(0.93);
}
.ks-svg {
  width: 20px;
  height: 20px;
  transition: all 0.18s ease;
}
.ks-svg path {
  fill: #c0c4cc;
  transition: fill 0.18s ease;
}
.key-star:hover .ks-svg path {
  fill: #e6a23c;
}

/* 点亮：金色渐变徽标 + 光晕 + 弹跳 */
.key-star.is-key {
  background: linear-gradient(135deg, #ffd666, #faad14);
  box-shadow: 0 3px 10px rgba(250, 173, 20, 0.5);
  animation: ks-pop 0.35s ease;
}
.key-star.is-key .ks-svg path {
  fill: #fff;
}
.key-star.is-key:hover {
  transform: scale(1.14);
}

@keyframes ks-pop {
  0% { transform: scale(1); }
  45% { transform: scale(1.25); }
  100% { transform: scale(1); }
}
</style>
