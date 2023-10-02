from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Do not allow to execute "./manage.py test"'

    def add_arguments(self, parser):
        parser.add_argument('-g', '--goku', dest='goku', action='store_true',
                            help='Kamehamehaaaaaaa!!')

    def handle(self, *args, **options):
        if options.get('goku'):
            self.write_goku()
        else:
            self.write_gandalf()

        self.stdout.write('Hey! If you want to run tests execute "pytest", '
                          'running "./manage.py test" will not use the test '
                          'settings in "src/setup.cfg" and will ask you to '
                          'delete the default database.\n\n')

        self.stdout.write('If you really want to execute "./manage.py test" '
                          'just delete me (src/main/management/commands/test.py) '
                          'and run "./manage.py test" again.\n\n')

    def write_gandalf(self):
        self.stdout.write("""
                                                                       `.
                                                                       ,;
                                                 .,                    ,i
                        `+`                      ;i                    .i
                        ;x#                      +#                    .*
                        +xx.                     nx`                   .*
                        ixx`                    ,xx:                   `+
                         #+                     ixx*                   `+
                         .*                     #xxz                    +
                          +                    `xxxx`                   #
                          +                    :xxxx;                   #
                          +`                 ``*xxxx+```                #
                          i,           :+#nxxxxxxxxxxxxxxnz+:           #
                          :;           ,zxxxxxxxxxxxxxxxxxxz:           #
                          .*             ,+xxxxxxxxxxxxxx+,          .,:z;:,
                           #               `:#xxxxxxxx#:`            .,:n:.`
                          `n:                ixxxxxxxx*                :x+
                          ;xx:zn*.           +xxxxxxxx#           .izn;nx#
                          ;xx*xxxx#;`        :xxMWWMxx;        `:#xxxx+nx:
                          ,xx,xxxxxxx#i:,.`.:#xx@##Wxx#:.`.,:i#xxxxxxx;`*.
                           ;# nxxxxxxxxxxxxxxxxM####Mxxxxxxxxxxxxxxxxx
                            # #xxxxxxxxxxxxxxxxW@WW@Wxxxxxxxxxxxxxxxxz
                            z *xxxxxxxxxxxxxxxx@####@xxxxxxxxxxxxxxxx+
                            +.:xxxxxxxxxxxxxxxx@####@xxxxxxxxxxxxxxxx;
                            i:`xxxxxxxxxxxxxxxx@####@xxxxxxxxxxxxxxxx.
                            :i #xxxxxxxn##zxxxx@####@xxxxz##nxxxxxxxz
                            .+ :xxx#i,`    .xxx@####@xxx,    `,i#xxx;
                            `z  ,.          nxx@####@xxx          .:
                             z              nxxW####Wxxx
                             #.             xxxM####Mxxx`
                             *:            .xxxx@##@xxxx,
                             ;i            :xxxxMWWMxxxx;
                             ,+            ixxxxxxxxxxxx*
                             `z            +xxxxxxxxxxxx#
                              n            nxxxxxxxxxxxxx
                              #.          .xxxxxxxxxxxxxx,
                              *:          ;xxxxxxxxxxxxxxi
                              ;i          +xxxxxxxxxxxxxx#
                              ,+          nxxxxxxxxxxxxxxx`
                              `n         .xxxxxxxxxxxxxxxx:
                               n`        ixxxxxxxxxxxxxxxx*
                               #.        #xxxxxxxxxxxxxxxxz
                               *;       `xxxxxxxxxxxxxxxxxx.
                               ;*       ;xxxxxxxxxxxxxxxxxxi
                               ,#       +xxxxxxxxxxxxxxxxxx#
                               `n      `xxxxxxxxxxxxxxxxxxxx`
                                n`     :xxxxxxxxxxxxxxxxxxxx;
                                #,     +xxxxxxxxxxxxxxxxxxxx#
                                `      nxxxxxxxxxxxxxxxxxxxxx`
                                      :xxxxxxxxxxxxxxxxxxxxxx;
                                      ,iiiiiiiiiiiiiiiiiiiiii:

 ,;: `::`
 `+;  i,
  :+``* `:;;;` ,;` ,;`  ,;;,.i: .i:  ,:  `;;`  :;,    ,i. `;:`:;;;` ;;;;;  ,i;;.  :,   :;;. :;;, `
   *:,, i,  :i .*  `;  `*  , *.  *.  i+`  i:   ,*      **` :.;:  ,*`:`+`.  `+ :i  **  ,i `,.i `,`i
   :+*`.*    *..*  `i  `+;`  i,``i. `:*,  i:   .*      ;:i :.+`   *,` +`   `+ :; .,+. .+:` .+:`  ;
   `*; .*    i,.*  `i   .i+, i;::*. :,;i  ;:   .*      ; i::,+`   ;:  +    `+:;` ;.i;  .i*. .i*. ,
    i: `*.   *``*  .;  .  ,i i.  i. ;,,+` i:  `,*  `   ; `*i.*,   i.  +`   `+   `i,:* .  ;;.  :; `
    i:  ,*..;:  i:`;.  ,:`:: *,  *,.;  *: *;`,:,+``i` `i` .*..*,`:;  `+.   .+`  ,: `+,:,.;,:,.;,`,
    ;;   `,,`    .:.   `.,. `,, `,.., `,,.,,,,.,,,,,  .,.  .` `,,.   .,,   .,.  ,. `,.`.,. `.,.  .
    i;
   .i;`


""")

    def write_goku(self):
        self.stdout.write("""
                                     `i`     `;@########W`   W@#.
                                    .:n.     .z#########W`   W##n`
                                    ,+@.    .iW#########W`  `@###z,`
                                    .x#:    :M##########@`` ,#####n.`             `,
                                   .iW#:   `*@##########@,` *######z.``          `n.
                                  .`z##:   ,M@#####@#####;.`n#######z.`         .xn
                                  :iM##i  `i@@###########+,.@########*`       `.x#*
                                  :n@##; `,x#@####@######M;:#########@,`     .,M##,
                                 `*W###;  :W######@######@i*####@#####M.`   `;W##W
                                 .z@###+  *@#####@@#######z###@#@######*`   iM###n
                                `:M@###x `z@##@@@@@#@#####@M##@#@######M.  :@####+
                                .z@@###x..M@##@#@@@@@#@####@####@@@@###@.`.x#####;
                               `:M@@###z,#W###@#@@@@@#@#########@@@@@@#@,`#@#####,
                               :+W@@#@@n,x@#@@@@@@@@@@@@@###@@##@@WW@@##;+@#####@`
                               :M@@##@@x:M###@@@@@@@@@@W@@##@W##@@WWWW@@*@@#####M
                               iW@@##@@M#W##@@@@@@@W@@@W@@##WW##@@WWWW@@W#######n
                             `,z@@@@@WWMz@##@@@@@@@W@@@W@@@#WW@#@@W@M@@@@#######+        `i:
                             `iM@@@@@WWMW@@#@@W@W@@@@@@W@@@@W@@#W@W@M@@@@#######;       `#x`
                             `#@#@@@@WWxW#@#@@W@W@@@@W@W@WWWW@@#W@W@M@@@@###@###,     `.z#;
                             ,n@@@@@@WMnW@@@@WW@W@@@@WWW@WWW@WW@WW@WW@@@####@@#@`    `,x#W`
                             `n@@#@@WWMzW@@@@WW@@W@WMWWW@MWW@WWMMW@WW@@@#@##@@#W    ,,x##+
                             .M@@@@@WMzxW@#@WWM@@W@WMWMWWMW@@WWMMW@WW@W@@@##@@#x   ,#x@#n`
                         ,,  .W@@@@@MM#xW@@@WWMW@WWxMWMWMx@W@M@MMW#W@WW@@@##@#@#   #M@#@:
                      ` `;i `;W@@@@WMn#xW@@@@WMW@@WnMMMWMnMW@M@MMW#W@WW#W@##W##* `,WW@@#
                      ``,#n `;W@@@@WM#xx@@@@@WMWW@WxMMMWMzxM@x@xMW#W@W@@W@#@@#@:`,M@@@x.
                       :.W@.`,W@@@@Wxzxx@@@@@WWMW@WMxMMMMznx@nWxMW@W@@@@@@#@@#@`.x@@@@:
                       ,:W#i`:W@@@@WzxnMW@@WWWMxWMWMxMWMM#zx@zWxMW@W#@@@@#@@@@W:xW#@@z
                        *W#x`,M@@@@nznnWW@@WWWnxWMWxxMWnM#zx@zWxxMWx#@@W@@@@@@Wx@@@#W,
                        :@#M:`x@@@@xz#nMW@@WMWnxMMMxxMMzM#znW#MnnnMx#WWWW@@@W@@#@#@@*`
                        .W#@*`#@@W@WzznMWW@WxMnxxMxxxxnzxz#nx#MznnMxWMMWMW@@WW@#@#@x`
                        `M#@x:#@@@WxznzMMWWWMxnnxMxnxnzzxn#zzzM#znMnWMMWMM@WMW##@@@;   ``
                        .x#@@*+@@WWxnznMWMxMMxnzxWnnnz#zxn###zn++nMxMMWWMW@MM@##@@M. `:,  `
                        ,n#@@xiW@WWxnznxWxxnxxnznxxzzz##nz#++#z**zMxxxWWMW@MW@#@#@*:.z*;  `     `;
                        .#@@W@nMMWWMnnnxWMxxnxnznzxz#z##zz+#*#z+*zxxxxW@MMWMM@@@@W#*nx+:.` .   `+*
                        `;@#@@@WMWMMxxzxWMnxxznznzxz#zz##z+#i#z+*znMxx@@WMWWWW@#@WW@@zM**::i...in:  `
                         ,x#@W@@WWWMxxnxWWnxMznznzxzzz#z##+#i#z#*znxxxW@WMWWMM@@#W@#Mnz#zzMn#+++#i````
                         `+#@WW@WWWMnxxnWMznMnz#nnxn#z#z#++##+##+znxxxWWMWW@MW@@@@#@xz##znn++#+*#i ..
                    `   .`,@#WM@WWWWxxxnMW#nxxz#nnnx#znn#++#n++++znxnznMMW@@WW@@###Mn###nz+zM#**+`,.`
                     .` `;;z#@WW@WWWMxxxnWnzxxnznnnzzzxn+++zM#+++#nzzzzxM@@@WW@###Wn####++M@@@n+i.,,     `
                      ;  ,Mx@#WW@WWMWxMxnMnznMnnnnn##zxMz#*xWMx+*###zz#xW@xxMW@##@xz##++#W@@@@@Mzi;. ``:.`
                      .i.;Mnx@@MW@WWWxMxxxxzzxxnnnn+#zxWxn+xWWWMzzzzzzzx@x+xMW@##Mz###+#@@@@@@@@@@W#;i+i,
                  `   `+znxz#W#WMW@@WWMMMnnnznnxxzz###nWWM#zxMMWMxMMxnzz@i**xW@#Wz###+n@@@@W@@WWWWWWMMMx`
              `..``,..,xn++++z@@WW@W@WMMMnzzz#nnnn#z+#zWWMx+#nxWxMMxzz+zM:;,+M@#nzn#+x@WMMMMWWMMxnnn+*#x`
               ..:;.*+nxnz+i;;z#@WWW@WWMMx###+znznzz++zxWMM#*#zzz#+++++zni*.;W@MnMz+zWMxxnxMxxxz*+nMMnin
               :::+xz##z+*i;;;ix@@W@WWWWMx##nnnnz#nxz+zzMMxM*+****++++++#,+i:W@xx#+zMxnnnnzz+*nnW@@@M#*z`
               `inMz####z****i*ix@@@@@MWMxnMMxnn##xMMz##zzxWn+++**i*xWn+#;n+,Wzn#+#xnnnz+i*#xMWMW@@WM*+#`
             ``,*xx#n@@@@@Wxnz*+#M@@@@@WWMxMMz++ii+xMWz+*zMWW+ii;;;nWWx+#,:*:xz+*+#++*i;+nMMMMMMM@@Wxiz#`
              .:nn++@@@W@@@@@Wnn#nW@@W@@WWMMxz+i;:,+nWM+i#xMWxi:::*WM#*+z,ii;#+i+#;::,;zxnxxxxMMMW@Wxin+`
              `+n#z@@Mz#zM@@@@@@MnzW@WW@@@WWMn+i:,,:zMWn++#nMWni.;Mx,,*+n;n;#+iiz;i:,;#zzzznxxMMMM@Wnix#
              .nzM@@W+;;;+MW@@@@@@xnWWWWW@@@Mxnz:,,,:nxM+*+znWMx#nM. `*+n*+*+i;#ii::i######znnWxxM@Wn+M,
           .`  iM@@@Wn+i**+nxxW@@@@MnMWWMnWWWMMWz,,,.,+MMxxMn#nnnWx*.`++z.;#ii+ii;,###+++++#zzxnnxWWzxi
           `,`  x@Wxn+*nnnnnxnz#nW@@@zxWn*+xMMn#zi,....*xMz::,.`#*...`++#i*;;**;+,iz##++#+++#znzznMWM+
           `.,.iMn++nMxnnnnznnnnzzM@@WMMn+n+ini,:+i....`..``:``.M#   ,#+z*;;;z:#::+#z**+***++zz###MW+
           `.*n#zxxnnnzzz####z#zxMMM@@@Wx;#+ii,,.:n#+;..```````*xM  ,+++#iii+*+ii##n#i;i:;+++zi+##Mx`
            ,n#nWWxnnz#z#+*+**nxxxzz#nxMW;;i#;....#WWWx*,````:iz`.`,*i;*#;#;#++inxMWz*i:,:**+#,izzM:
            ,xzW@Wnnz####;,.#xxxzz##++##zz;:#z....;n;;#MW#*::;#,``,*:,,i#;#i+z;nMMMMMn*:.;;+z,,+#xz,
            .zx@@Wnzz##*;;` #xnzz#+*ii*+#zz:*x:``..+.  `+Wn#z++i..,...,;+;#+z*+nnznnxxx:;,:z+;*+nn#`  ` `
            ,#nM@Wnz#+*:.`:`;xz##*:,..,;*#zn*ni````:;   `i..i**,.````..:+;+##+#####zzxM#i.+#***+#ni,`.`.`
            `+nxWWxz#+i,``.:.nz+i:.````.;+#zni+````.;``,,:;,.:,:``.,``.i#i*z**iiiii*#nnMz;+#+#**z#n::.:`
             ;nnxWxxn#z+zii+##z*:.`    `,+#zz+i;...`,+*iii:.```*+`.#``.#zii**;:::::;*#zxMi:;+i***zz*,i.
             :xnnWn#*;*#++**i;;#:``   `.:nxnxnnn;,``.ii,.`````,*#,:W.`.Mxiiz;:,,,,,:;*#zx;..:;*ii+nzi.
             .xnnMnz*i*+#**i:.`i+.`,;:,*##nznzzn#`  `:*.```:..,i::i*,`:WW*in:,,,,,,,,;*zni...:i*+##n:.
             .#nnxxz+++#++*;.` `ii+xx#+#++++*zz+z:` `,*:```*,..,+**.,`+W@*iz,,,,,,,,,:i#zi`...;*#+#zi`
             `;nnnzz+#zzz*i:`   .*zM#*:;#*:..,***+`  .;+..`+W#i*i:;:,.xW@#i*,,..,,,,,,;*z*`...:++*+z+`.`
               innnn#+zxz+i,`   `,xn+:;.,#:` `.:;+:` `,ii.``z;;,::i:.ixWx#*i,.....,,,,:i#*....,i++#z+,`
                ,znnx##nM#i,`   `i#+;.:i`.+*```,;++..:..#,.``:,ii;,,,zxW###*.......,,,:i+z:`..,i+z+z#` `.
                `,nxnn#zxn*,`   `*i;.`*;,`.ii.:*inn,`.``izi,.`,...::*nMx*+n*,.......,,,;+z``..,i+z#z#.,,`
                 `,+nxz#xn+:,`  `:,.``;`,.``:*#xxz#,`  `.#WMz*,,:::;znM+i#x##..``....,,;#z,`..,i+n##*;..`
                    `###nnz*i.   .``.;`` . ``ix##nx;`  .`:xz#zxn+##+*z#;*z:;+z````...,,:*x,...,i+n#z+.,    ``
                    `*z##xz+#,    `,,,*.``.:``inxMMi`  `..#+;:i#z#;;ni;;;,``.#````...,,:*z:,..,i#n#n*.   .+*`
                     +n#+nx#+;``..`  `i*.:*` ``+MMxi`  `,.:nz#+;:;+x*;i,`   ,i`````.,,,:*z;...,i#n##` `,#Wi
                     .n#*;nz+i`.`.,` `,#z:``   `;n+;` .`;..iz*+zznn#;;#`    ;.`````,,,,;##,...:*zn+z.*x@W:
                     .n#+;ix#*`.,`.;.,+xx:`     `.,,` ``.``.*z#nxn*i;+*    `i``.``,,.,,*z:`...;+zzz#x@@M,
                     .zz#+;xx#, .ii,:;#n;n.`      ``.   ````,#MWM#;;;z.   `,i`.``,,.,,;+*....:*#xzxW@@M.
                      iMz#;nx#;` `:*+#x;#M*.`       `    ` `.izxii;;iz`   `+*..`,:.:i;+n+;:i;i*znzWW@W,
                      `zxz+zx#*.  ``.##iMMM*.`  `.       `  `,;#*i;in+;   ,z#;.;:`*i;:;:;i*ii*+z+nW@@+
                       ,xnznxz*;. ` .n*#MnxM:.``,,         ```.;###xz..` `i*n*+i**;:,,:::::;i*+++xW@@.
                        :nnnMn+*i:...n;zxnMM;.,;.`  .`    `i``.:,++#;`   .#i*;;++::,,,,,,:;;i*#++M@@M
                        `;+xMn#+zz+**x+nxMMz:..``  `,     .,   `,,:,.    ,+:::;#::,.....,,:;i*zz#W@@n
                          `,zxznn#*:i*+##+i,.``   `:`    `,`      `     `#:,,,*;:...`....,:;i+nz#x@@n
                          ,:.nxx#,.```.`.`,.``    `;`   `,.             ,#.`..:,.``````..,::i+nn#z@@+
                      `,`.*#nnWzz*.,`    ``:      .,    ,,`             i;```...```````..,:;i*zn#n#,
              .+x#. `;+xWWWWWWMz#+;`:``.   :     `,`   .:.`             ;, `...:i;``````.,:;i+nnzn:
             `;MMWM+xWWMMMxxnnxz##*,,:.:  `:     `,`   :.,`            `*,;+#zxMWMni.`.,:::;i*nnzz;
             ,xMMMWMMMxxnz####nx##+;.i;`  `.     `.    .`:`           `;zz+i;*znnxWWMnx#::;ii+n#++i`
            .zMnxMMxxnz##+++++#nn##i,i;`  `      ``   `` :`           `*;::,::*nnn+;:,ixi:;i*zn++z;`
          `,,xn#zMxnz#++++******nxzi+nx:`        ``   ;` ,`           ,i::,,,:#*,.````:xi;i*#xz*++
         .:zxx##zxz##+***iiiiii**xM#zx@x,`       `    :  :`           ;n#i:,;i:`     `,+nii*++**z+...`
       .:nWMnnz#+nz#+**iiiiiiiiii*xMxxMWi`           `,  :`          .xMx+;i:``     `.,#xz++i;i#n+,,.`
    `::zWWxn##n#++z+**iiiiiiiiiii**#znxWi`           ..  ,`          ;Wxn*,`   `    `.+x+x#::;*zxi.`
   .,+WWMxz#++#n+*z+iiiiiiiiiiiiiiiii*#n,`       `   :.  `,         .xxz*,`    ,.  `.:xM+z+.:i#nxi;;`
    iWMxn#+****+n+*+iiiiiiiiiiiiiiii*#n*` ``     ,   :`  `:`       `+*;,.`     `:``.iznn#+n;;*zxMi``
  `*@Wx#+***ii**nn**iiiiiiiii;;;;iii#M*.` `,`   `,  `;`   .:     `. ```       ``:+ii;innn*Mz#znxMWn*:.`
`.,nWM#***iiiiii*n#ii*i;;;;;;;;ii*+#n*.    :.   `,  `:    `:`   `:.     `     `.i#:,:*nnn#x#+nnxMnM+,`
..,xMx+**iiiiiiiii+*;i##i;;;;;;;;;*x+.`  ``*:```;.  `;     `,  :i.      `:`   `;+i*,:znnnznnzznMxnnxi:
   +Mx+*iiiiiiiiii;;i;;i+#*;;;;;;;n#,`  `;.,:.`.;   `,      ` ,i,        `::``.+i:#*;znnnxxMz#znz##nM+;:,`
   .xx#**iiiiiii;;;;;;;;;;+#i;;;;ixi.,,::i,i+i;*,`  `,        .``         `.;.:zi;*n+nnnnMMWz#zz####nx;:,`
   `#Mn+**iiiiiiii;;;;;;;;;i*+i;;*x*,,..:*i;+z##*;,`.`       `               ``+i:;nnnnnMWWM#+#*ii**+xnz*:`
``.*WMxz+*iiiiiii;;;;;;;;;;;;;;i;#M#++*;.:;;;i*+nn+i,```  ```  ``             `,z;:nxnnnM@WM##****ii*#Mn+*,
  .*WMxn+**iiii;;;;;;;;;;;;;;;;;;;znz##+i,;;;i**+#zz*i*,,;+,`  `.             `,z#:+WxnMW@@W#i;;iiiii*zxxxW:.`
 `,MWMnnz+*i;;;;;;;;;;;;;;;;;;;;;;iMMxnz#*;;;*ii+###nxxxWM,     :`             `:z+*MMxW@@@M*;;;;;i**#nz##n;`
  *WMx#+#+i;;;;;;;;;;;;;;;;;;;;;;;;i++##i;;;;i**+z###nMWM,      `;`          ````:x+MWW@@@W+;;;ii*+#zn**#nxz:`
 .#WMx#+++iii;;;;;;;;;;;;;;;iii*+i;++*ii;;;;;ii*+#znznMW#`       .,.`      ..,:```:zM@@@@M+ii*+####+ii;i+#z#,`
 ,+WMn+*+*i;;*i;;;;;;;;;;;;;;;;;;;i;;*##**i+##****+zMxMx;`        `;;:.,:;`..`    `*W@@Wziiii***i;i;;;i#zzx+.
.:+WMn#+*ii;;i#*i;;;;;;;;;;;;;;;;iiiiiiiii**+##zzzznMMMn;`         ``:i:``   ``    .;xz**;;;;;;;;;;;ii*nz#nz+.
..`+xz#+*ii;;izM#i;;;;;;;;iiiiii*********++**+###nxxMMzni`       `.,,.`         ,` `.ii+i;;;;;;;;;;ii*+++##nW;`
   ,xz#+***iii*xM#*i;;;iii*****++++###+#z+##zzxxxxn++,`#:`    `,,,.`          `..  `,``.;+i;;;;;iii*i****+znW+,
    *xz#+*++**+#MMx+*iiiii**#zxxMMMMMxx#nx#nz;;+i:,`.`.#.  `,;:``            `:`   ,` ``.+*+iii*+****iiii*#zMi:.
    :xn#+++#####zMMn#**iii**#nxxMM@WWWxM@W*:` ..       z. `,.              `.:`   ``   .*. .iz##+++**iiii*+nM:```
     :nzz###nz###xMMMxz****++#zxWWWWWWWWWW:           .#,`,`               ,.`    `    ,`    `i+;;;;;;iii**#xi,.
    `,+xn#++#nn##zxMWW@WWn+*++zxMMWMxxMMMW`           .*:``                       ```  `     ,*;#*;;;;;i*i*+nn*``
   `.``;xnzz#zxMz#zxWWW@WWWxnxxMWMnnnnxxM#             i;`              .        ```````    .:`.,**;;;;iii*#nMWi`
       .#xxxn#zMWMnnxMMMMMMMMWWn#####nxxz`             i*`           `,,`       `;+***:.`   ,` `.,*+;;;;ii*+nxW*,
       ` :nMxnzznxMWWWWWWMWWW@Wxz++*#nMz.              ;+`        `..:`         `*;;;ii+;:``.  `.,:zi;;;ii*#zzW**:`
         `,i#nMMxnnnxMMMW@@WnMz;iii*zxn,`              .#``..,,:;:;,`           `*i;;;;;*+#;`` `..,++;;;;**z#zM+*...`
       `,,`  ;ii+xMMMMWW@@xinz;;ii*#xxi`               `z;,.,.,````          `;.`;+;;;;;;;#n#,``.,,+z;;;;*###zM;,.
      ..      ```;xWWx*W@Wi#n;;ii*+zxi`                `+`        `         `i`  .#*;;;;;;;;#zi:,,:n+;;;*#zz#nM,:.
                  `;,`*@@*+xiiii*#zx;                  `+`        `         ,`   `:z*;;;;;;;;ii*#nx+;ii#n++##nM,.
                     ;M@#*Mn##+#nnx*.                  .+``                `.    `,i**i;;;;;;;;;;;i;ii+++++##nMi`
                    `#@zixMxxxnxxM#:`                  .i.`              ``..   `i;.*;*+i;;;;;;ii;ii*+*i*i###zxx+.
                    .nWinWMMMMMxx#:`                   `i,`          ``.`.ixx: `;.` .*;i**;;;;;ii*++*+i;i##+##zxMMi
                    ;z+#@WWMxz*;i.`                     *,`    ```  .::.`:MMMx:..`` `,i;;;**i+++**+*;;i**ii+*+#znMM`
                   `;*i+#*i*+;,i`                       *;,` ```....,`.``:@MMxz,   ```ii;;;+zi*i;i;**iii;;;i*++##xM`
                   .;+*i;;+i:.:`                       `;;.` `.;+z+,` ```.nWMMn#.  .i:.#;;;;i+++*iiiii;;;;;ii*+##zM,
                  `;#*, `,.``.                        `*:::` `i.`.,;`  ``.+*@Mxz+``;,``+i;;;;;i+#*;;;;;;;;;iii*##zM+.
                  ,;;`  .                             ,i.`;*`.+    .: .:,`+.#WMx#i..  `;+;;;;;;;i***i;;;;;iiii+##zxW:
                  .`                                  ;:,.`*`;+     i,;.``*..*zMnn,   `,z;;;;;;;;;ii*+*******+##nnxW+,
                                                      *i;,`:.+:     ,:.` `;, `.zMx+````.+z;;;;;;;;;;;;+z##zznznxnxMW+,
                                                      ##+;...+     ```;*``,:   *xzz:...,+#*;;;;;i*ii;;;;i+####zzxMMW+,`
                                                      z##i,`i;     ,`.,;``:i   ,x#+#;,,;z#i;;;;;;i+++i;;;;ii*+++xMMW+:.
                                                     `#z#*::#      :.,,..`.i   .nz+#zz+zM#ii;;;;;;;;*z+iiiii*++#nMMW#;.
                                                      .;##z#:      i;;::,.`:   `*n####nnz*iiii;;;;;;;iz#*iii*++#nMMWi:`
                                                        ,:i`       .:z+*i,:.    .xz####++**iiiii;;;;;;;*##+*+##zxMMMi.
                                                          `          ;z#+++,     #xn###+++++**iiii;;;;ii***+znnxMMW@z*.
                                                                     `.+z#,`     :xxxz###+++++***iii;iiii***+#zxMM@@@W+.
                                                                        `.       `:zMMnzz#++++******iii***+++zxMMW@@@@zi
                                                                                   :@@WMxn##++++********++++#nMMW@@WWWzi`
                                                                                   .@@@@WWn###+++++***+++++#zxMM@WMMMWx*.
                                                                                   :MWWWWWWnz###+++++++++##zxMMWWMMMxMM:i,
                                                                                   ;WWMMWMMMMxnn##+++++##znxMMM@WMMMMMM+;:.
                                                                                  `+WMMxMWnznxMMxxnz#zzznxxMMW@WMMMMMM+,;;`
                                                                                  .*WMMxzMMz##znMMMMxMMMMMMxMW@WMMMMMxi:`.
                                                                                   iWMMx#nMxzz++zxMMMMMMMMMM@@WMMMMMx:i;.
                                                                                   i@MMx##nxMMz##zxMMMMMMMM@@WWMMWMMn`.;,
                                                                                   :@WMMz##nxMMMxxxxMMxMMMWWWMMMMWMWW;``,.
                                                                                   .@WMMn####nnnxxMMMMMMMWWMMMWMWWM@@*;``
                                                                                    x@WMxnz####znnMMxxxxMMMMMMWM@MW#@;:.
                                                                                    .x@WWMxxxxxxxMMMxznMMMMMMMMWMM@@@n,.`
                                                                                     .inM@MMMMMMMMMMxznMMMMMMWMWM@##@ni```
                                                                                      .:,zWMMMMMMMMMMxxMMMMMMMMMM@##@x:,``

""")
