import { ref, onMounted, onUnmounted } from 'vue'

export function useMouseEffect(containerRef) {
    const mousePos = ref({ x: 0, y: 0 })
    const isActive = ref(false)

    const handleMouseMove = (e) => {
        // 如果没有传入container，则相对于窗口，否则相对于容器
        if (!containerRef?.value) {
            mousePos.value = { x: e.clientX, y: e.clientY }
        } else {
            const rect = containerRef.value.getBoundingClientRect()
            mousePos.value = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            }
        }
        isActive.value = true

        // 如果有容器，检测其中的文字元素并进行放大效果
        if (containerRef?.value) {
            detectNearbyText(e.clientX, e.clientY, containerRef.value)
        }
    }

    const handleMouseLeave = () => {
        isActive.value = false
        if (containerRef?.value) {
            const textElements = containerRef.value.querySelectorAll('h1, h2, p, span, a')
            textElements.forEach(el => el.classList.remove('enlarged'))
        }
    }

    const detectNearbyText = (x, y, container) => {
        // 限制检测的元素类型，避免性能问题
        const textElements = container.querySelectorAll('.interactive-text, h1, h2')
        const threshold = 150 // 增大检测范围

        textElements.forEach(el => {
            const rect = el.getBoundingClientRect()
            const centerX = rect.left + rect.width / 2
            const centerY = rect.top + rect.height / 2
            const distance = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2)

            if (distance < threshold) {
                // 计算缩放比例，距离越近缩放越大
                // const scale = 1 + (1 - distance / threshold) * 0.1
                // el.style.transform = `scale(${scale})`
                // 简单起见，使用类名切换
                el.classList.add('enlarged')
            } else {
                // el.style.transform = 'scale(1)'
                el.classList.remove('enlarged')
            }
        })
    }

    return {
        mousePos,
        isActive,
        handleMouseMove,
        handleMouseLeave
    }
}
