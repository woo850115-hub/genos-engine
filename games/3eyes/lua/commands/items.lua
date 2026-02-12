-- items.lua — 3eyes item commands (wear, wield, remove)
-- Overrides common items.lua for 3eyes-specific wear slot messages

local SLOT_NAMES = {
    [0]="머리", [1]="목", [2]="가슴", [3]="몸통",
    [4]="다리", [5]="발", [6]="오른손", [7]="왼손",
    [8]="오른팔", [9]="왼팔", [10]="방패", [11]="허리",
    [12]="오른손목", [13]="왼손목", [14]="오른손가락", [15]="왼손가락",
    [16]="무기", [17]="보조무기",
}

register_command("wear", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 착용하시겠습니까?")
        return
    end
    if args == "all" or args == "전부" then
        ctx:wear_all()
        return
    end
    local item = ctx:find_inv_item(args)
    if not item then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end
    local slot = ctx:wear_item(item)
    if slot then
        local slot_name = SLOT_NAMES[slot] or ("슬롯 " .. slot)
        ctx:send(item.name .. "을(를) <" .. slot_name .. ">에 착용합니다.")
    end
end, "착용")

register_command("wield", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 들으시겠습니까?")
        return
    end
    local item = ctx:find_inv_item(args)
    if not item then
        ctx:send("그런 물건을 가지고 있지 않습니다.")
        return
    end
    local slot = ctx:wield_item(item)
    if slot then
        ctx:send(item.name .. "을(를) 무기로 장비합니다.")
    end
end, "들")

register_command("remove", function(ctx, args)
    if not args or args == "" then
        ctx:send("무엇을 벗으시겠습니까?")
        return
    end
    local item = ctx:find_equip_item(args)
    if not item then
        ctx:send("그런 장비를 착용하고 있지 않습니다.")
        return
    end
    ctx:remove_item(item)
    ctx:send(item.name .. "을(를) 벗습니다.")
end, "벗")
